package ledger

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"sync"
	"testing"
)

func resolverFixtureUsage() Object {
	return Object{
		"schema_version": "0.1", "provider": "openai", "surface": "openai.chat_completions",
		"model": Object{"requested": "gpt-test", "returned": "gpt-test", "billed": "gpt-test", "alias_resolution": "none"},
		"components": []any{
			Object{"name": "input_uncached_tokens", "quantity": "1000", "unit": "token"},
			Object{"name": "output_text_tokens", "quantity": "500", "unit": "token"},
		},
	}
}

func TestExternalPriceResolverLifecycle(t *testing.T) {
	var lock sync.Mutex
	mode := "normal"
	calls := []string{}
	conditionalETag := ""
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		lock.Lock()
		calls = append(calls, request.URL.Path)
		conditionalETag = request.Header.Get("If-None-Match")
		currentMode := mode
		lock.Unlock()
		if currentMode == "not-modified" {
			writer.Header().Set("ETag", `"fixture-v2"`)
			writer.WriteHeader(http.StatusNotModified)
			return
		}
		if currentMode == "fail" {
			http.Error(writer, "fixture failure", http.StatusBadGateway)
			return
		}
		writer.Header().Set("Content-Type", "application/json")
		writer.Header().Set("ETag", `"fixture-v1"`)
		var payload any
		if request.URL.Path == "/genai" {
			payload = Object{"providers": []any{Object{"id": "openai", "models": []any{Object{"id": "other", "match": Object{"equals": "other"}, "prices": Object{"input_mtok": "9", "output_mtok": "9"}}}}}}
		} else {
			payload = Object{"openai": Object{"models": Object{"gpt-test": Object{"cost": Object{"input": "1", "output": "2"}}}}}
		}
		if err := json.NewEncoder(writer).Encode(payload); err != nil {
			t.Errorf("encode fixture response: %v", err)
		}
	}))
	defer server.Close()

	cacheDir := t.TempDir()
	options := Object{
		"usage_ledger": resolverFixtureUsage(),
		"sources":      []any{"genai-prices", "models.dev"},
		"source_urls": Object{
			"genai-prices": server.URL + "/genai",
			"models.dev":   server.URL + "/models",
		},
		"cache_dir":   cacheDir,
		"http_client": server.Client(),
		"now":         "2026-07-18T00:00:00Z",
	}
	resolution, err := ResolvePriceCatalog(context.Background(), options)
	if err != nil {
		t.Fatal(err)
	}
	if asString(resolution["selected_source"]) != "models.dev" {
		t.Fatalf("expected models.dev fallback, got %#v", resolution)
	}
	if len(calls) != 2 {
		t.Fatalf("expected ordered source calls, got %#v", calls)
	}
	for _, rawCard := range asSlice(resolution["price_cards"]) {
		if asString(asObject(asObject(rawCard)["source"])["name"]) != "models.dev" {
			t.Fatalf("resolver mixed source cards: %#v", resolution["price_cards"])
		}
	}

	freshOptions := cloneObject(options)
	freshOptions["sources"] = []any{"models.dev"}
	freshOptions["now"] = "2026-07-18T01:00:00Z"
	fresh, err := ResolvePriceCatalog(context.Background(), freshOptions)
	if err != nil {
		t.Fatal(err)
	}
	if len(calls) != 2 || asString(asObject(asSlice(fresh["sources"])[0])["status"]) != "cache_fresh" {
		t.Fatalf("fresh cache fetched unexpectedly: calls=%#v resolution=%#v", calls, fresh)
	}

	lock.Lock()
	mode = "not-modified"
	lock.Unlock()
	validatedOptions := cloneObject(freshOptions)
	validatedOptions["refresh"] = true
	validatedOptions["now"] = "2026-07-18T02:00:00Z"
	validated, err := ResolvePriceCatalog(context.Background(), validatedOptions)
	if err != nil {
		t.Fatal(err)
	}
	if asString(asObject(asSlice(validated["sources"])[0])["status"]) != "cache_validated" || conditionalETag != `"fixture-v1"` {
		t.Fatalf("conditional validation failed: etag=%q resolution=%#v", conditionalETag, validated)
	}

	lock.Lock()
	mode = "fail"
	lock.Unlock()
	staleOptions := cloneObject(validatedOptions)
	staleOptions["now"] = "2026-07-20T00:00:00Z"
	stale, err := ResolvePriceCatalog(context.Background(), staleOptions)
	if err != nil {
		t.Fatal(err)
	}
	if asString(stale["selected_source"]) != "models.dev" || asString(asObject(asSlice(stale["warnings"])[0])["code"]) != "price_source_refresh_failed" {
		t.Fatalf("last-known-good fallback failed: %#v", stale)
	}

	beforeOffline := len(calls)
	offlineOptions := cloneObject(freshOptions)
	offlineOptions["offline"] = true
	offlineOptions["now"] = "2026-07-20T00:00:00Z"
	offline, err := ResolvePriceCatalog(context.Background(), offlineOptions)
	if err != nil {
		t.Fatal(err)
	}
	if len(calls) != beforeOffline || asString(asObject(asSlice(offline["sources"])[0])["status"]) != "cache_stale" {
		t.Fatalf("offline resolver accessed network or hid stale cache: %#v", offline)
	}

	response := Object{"model": "gpt-test", "usage": Object{"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}}
	auto, err := FromResponseAuto(context.Background(), response, Object{
		"provider": "openai", "surface": "openai.chat_completions", "sources": []any{"models.dev"},
		"source_urls": options["source_urls"], "cache_dir": cacheDir, "offline": true,
	}, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if asString(auto["total"]) != "0.002" || asString(asObject(asObject(auto["metadata"])["price_resolution"])["selected_source"]) != "models.dev" {
		t.Fatalf("auto response pricing failed: %#v", auto)
	}

	status, err := PriceCacheStatus(Object{"cache_dir": cacheDir})
	if err != nil || len(asSlice(status["entries"])) == 0 {
		t.Fatalf("cache status failed: %#v %v", status, err)
	}
	cleared, err := ClearPriceCache(Object{"cache_dir": cacheDir, "sources": []any{"models.dev"}})
	if err != nil || len(asSlice(cleared["removed"])) == 0 {
		t.Fatalf("selective cache clear failed: %#v %v", cleared, err)
	}
}

func TestExternalPriceResolverOfflineMissAndExplicitCards(t *testing.T) {
	explicit := []any{Object{
		"schema_version": "0.1", "id": "openai:gpt-test:user", "provider": "openai", "model": "gpt-test",
		"components": []any{Object{"usage_component": "input_uncached_tokens", "unit": "token", "price": Object{"amount": "1", "currency": "USD", "per": "1000000"}}},
		"source":     Object{"name": "user", "url": "https://example.com/contract", "retrieved_at": "2026-07-18T00:00:00Z"},
	}}
	resolved, err := ResolvePriceCatalog(context.Background(), Object{"price_cards": explicit, "http_client": &http.Client{Transport: panicRoundTripper{}}})
	if err != nil || asString(resolved["selected_source"]) != "user" {
		t.Fatalf("explicit cards did not bypass network: %#v %v", resolved, err)
	}
	empty, err := ResolvePriceCatalog(context.Background(), Object{"price_cards": []any{}, "http_client": &http.Client{Transport: panicRoundTripper{}}})
	if err != nil || asString(empty["selected_source"]) != "user" || len(asSlice(empty["price_cards"])) != 0 {
		t.Fatalf("explicit empty cards did not bypass network: %#v %v", empty, err)
	}
	missing, err := ResolvePriceCatalog(context.Background(), Object{
		"usage_ledger": resolverFixtureUsage(), "sources": []any{"models.dev"}, "offline": true,
		"cache_dir": t.TempDir(), "source_urls": Object{"models.dev": "https://example.com/models.json"},
		"http_client": &http.Client{Transport: panicRoundTripper{}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if missing["selected_source"] != nil || asString(asObject(asSlice(missing["warnings"])[0])["code"]) != "price_source_unavailable" {
		t.Fatalf("offline cache miss was not visible: %#v", missing)
	}
}

func TestLiveExternalPriceSources(t *testing.T) {
	if os.Getenv("RUNCOST_LIVE_PRICE_SOURCES") != "1" {
		t.Skip("set RUNCOST_LIVE_PRICE_SOURCES=1 to verify current public datasets")
	}
	cacheDir := t.TempDir()
	for _, source := range []string{"genai-prices", "models.dev", "litellm", "openrouter"} {
		t.Run(source, func(t *testing.T) {
			resolution, err := ResolvePriceCatalog(context.Background(), Object{
				"sources": []any{source}, "cache_dir": cacheDir, "refresh": true,
			})
			if err != nil || asString(resolution["selected_source"]) != source || len(asSlice(resolution["price_cards"])) == 0 {
				t.Fatalf("live source resolution failed: %#v %v", resolution, err)
			}
		})
	}
}

type panicRoundTripper struct{}

func (panicRoundTripper) RoundTrip(*http.Request) (*http.Response, error) {
	panic("offline or explicit resolver attempted network access")
}
