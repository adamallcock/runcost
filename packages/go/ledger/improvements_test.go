package ledger

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func improvementCard(component, url string) Object {
	return Object{"schema_version": "0.1", "id": component, "provider": "openai", "model": "probe", "components": []any{Object{"usage_component": component, "unit": "token", "price": Object{"amount": "1", "currency": "USD", "per": "1"}}}, "source": Object{"name": "same", "url": url}}
}
func improvementUsage() Object {
	return Object{"schema_version": "0.1", "provider": "openai", "surface": "openai.responses", "model": Object{"requested": "probe", "returned": "probe", "billed": "probe", "alias_resolution": "none"}, "components": []any{Object{"name": "input_uncached_tokens", "quantity": "1", "unit": "token"}}}
}

func TestImprovementMoneyPolicyValidationBeforeRounding(t *testing.T) {
	expectExpansionPanic(t, "budget must be non-negative", func() {
		EvaluateBudget("0", Object{"budget": "-0.0000000000000000001"})
	})
	expectExpansionPanic(t, "warning_threshold must be between", func() {
		EvaluateBudget("0", Object{"budget": "1", "warning_threshold": "1.0000000000000000001"})
	})
	expectExpansionPanic(t, "tolerance must be non-negative", func() {
		ReconcileCost("0", "0", Object{"tolerance": "-0.0000000000000000001"})
	})
}

func TestImprovementOwnershipProvenanceAndErrors(t *testing.T) {
	usage := improvementUsage()
	input := improvementCard("input_uncached_tokens", "https://example.com/a")
	compiled := CompilePriceCatalog([]any{input})
	asObject(asObject(asSlice(input["components"])[0])["price"])["amount"] = "99"
	asObject(asObject(asSlice(asObject(compiled.PriceCards[0])["components"])[0])["price"])["amount"] = "98"
	if result := calculateCostWithCompiledOptions(usage, compiled, nil, Object{}); result["total"] != "1" {
		t.Fatalf("catalog mutation: %#v", result)
	}
	usage["components"] = append(asSlice(usage["components"]), Object{"name": "output_text_tokens", "quantity": "1", "unit": "token"})
	result, err := CalculateCostWithOptionsE(usage, []any{improvementCard("input_uncached_tokens", "https://example.com/a"), improvementCard("output_text_tokens", "https://example.com/b")}, nil, Object{"mode": "strict"})
	if err != nil || len(asSlice(result["price_sources"])) != 2 {
		t.Fatalf("source identity: %#v %v", result, err)
	}
	for _, adjustment := range []Object{{"type": "typo", "value": "50"}, {"type": "multiplier", "value": "bad"}} {
		if value, err := CalculateCostWithOptionsE(improvementUsage(), []any{improvementCard("input_uncached_tokens", "a")}, []any{Object{"id": "invalid", "adjustment": adjustment}}, Object{}); err == nil || value != nil {
			t.Fatalf("invalid discount accepted: %#v %v", value, err)
		}
	}
	result["metadata"] = Object{"secret": "PRIVATE_SENTINEL"}
	result["attribution"] = Object{"tenant_id": "PRIVATE_SENTINEL"}
	result["warnings"] = []any{Object{"code": "usage_missing", "message": "PRIVATE_SENTINEL", "metadata": Object{"field": "PRIVATE_SENTINEL"}}}
	shared := ExportCostLedger(result)
	encoded, _ := json.Marshal(shared)
	if string(encoded) == "" || asObject(shared["metadata"])["secret"] != nil || asObject(result["metadata"])["secret"] != "PRIVATE_SENTINEL" {
		t.Fatal("export ownership/redaction failed")
	}
}

func TestImprovementConcurrentResolverAndStrictErrors(t *testing.T) {
	var calls atomic.Int32
	var fail atomic.Bool
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
		time.Sleep(30 * time.Millisecond)
		if fail.Load() {
			http.Error(w, "controlled refresh failure", 503)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`[{"id":"openai","models":[{"id":"probe","prices":{"input_mtok":1,"output_mtok":2}}]}]`))
	}))
	defer server.Close()
	options := Object{"provider": "openai", "sources": []any{"genai-prices"}, "source_urls": Object{"genai-prices": server.URL}, "cache_dir": t.TempDir(), "now": "2026-10-04T00:00:00Z"}
	response := Object{"object": "response", "model": "probe", "usage": Object{"input_tokens": 1, "output_tokens": 0}}
	var group sync.WaitGroup
	for i := 0; i < 8; i++ {
		group.Add(1)
		go func() {
			defer group.Done()
			value, err := FromResponseAuto(context.Background(), response, options, nil, nil)
			if err != nil || value["total"] != "0.000001" {
				t.Errorf("cold quote: %#v %v", value, err)
			}
		}()
	}
	group.Wait()
	if calls.Load() != 1 {
		t.Fatalf("cold fetch count: %d", calls.Load())
	}
	public, err := ResolvePriceCatalog(context.Background(), options)
	if err != nil {
		t.Fatal(err)
	}
	asObject(asObject(asSlice(asObject(asSlice(public["price_cards"])[0])["components"])[0])["price"])["amount"] = "999"
	value, err := FromResponseAuto(context.Background(), response, options, nil, nil)
	if err != nil || value["total"] != "0.000001" {
		t.Fatal("public resolution poisoned cache")
	}
	fail.Store(true)
	strict := cloneObject(options)
	strict["refresh"] = true
	strict["mode"] = "strict"
	if value, err := FromResponseAuto(context.Background(), response, strict, nil, nil); err == nil || value != nil {
		t.Fatalf("strict refresh warning returned success: %#v %v", value, err)
	}
	estimate := cloneObject(strict)
	estimate["surface"] = "openai.responses"
	estimate["model"] = "probe"
	estimate["components"] = Object{"input_uncached_tokens": "1"}
	if value, err := EstimateCostAuto(context.Background(), estimate, nil, nil); err == nil || value != nil {
		t.Fatal("strict estimate accepted warnings")
	}
	span := Object{"attributes": Object{"gen_ai.system": "openai", "gen_ai.response.model": "probe", "gen_ai.usage.input_tokens": 1, "gen_ai.usage.output_tokens": 0}}
	if value, err := FromOTelGenAISpanAuto(context.Background(), span, strict, nil, nil); err == nil || value != nil {
		t.Fatal("strict OTel accepted warnings")
	}
	items := []any{Object{"custom_id": "a", "response": Object{"status_code": 200, "body": Object{"model": "probe", "usage": Object{"prompt_tokens": 1, "completion_tokens": 0}}}}}
	strict["endpoint"] = "/v1/chat/completions"
	if value, err := FromBatchResultsAuto(context.Background(), items, strict); err == nil || value != nil {
		t.Fatal("strict batch accepted warnings")
	}
}

func TestImprovementBatchCoverageUsesAllModels(t *testing.T) {
	var calls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
		w.Header().Set("Content-Type", "application/json")
		if r.URL.Path == "/genai" {
			_, _ = w.Write([]byte(`[{"id":"openai","models":[{"id":"probe","prices":{"input_mtok":1,"output_mtok":2}}]}]`))
		} else {
			_, _ = w.Write([]byte(`{"openai":{"models":{"probe":{"cost":{"input":1,"output":2}},"second":{"cost":{"input":1,"output":2}}}}}`))
		}
	}))
	defer server.Close()
	items := []any{}
	for index, model := range []string{"probe", "second"} {
		items = append(items, Object{"custom_id": fmt.Sprintf("item-%d", index), "response": Object{"status_code": 200, "body": Object{"model": model, "usage": Object{"prompt_tokens": 1, "completion_tokens": 0}}}})
	}
	value, err := FromBatchResultsAuto(context.Background(), items, Object{"provider": "openai", "endpoint": "/v1/chat/completions", "sources": []any{"genai-prices", "models.dev"}, "source_urls": Object{"genai-prices": server.URL + "/genai", "models.dev": server.URL + "/models"}, "cache_dir": t.TempDir()})
	if err != nil || asObject(asObject(value["metadata"])["price_resolution"])["selected_source"] != "models.dev" || calls.Load() != 2 {
		t.Fatalf("batch source coverage: %#v %v calls=%d", value, err, calls.Load())
	}
	for index, raw := range asSlice(value["items"]) {
		item := asObject(raw)
		if item["id"] != fmt.Sprintf("item-%d", index) || asObject(item["ledger"])["total"] == "0" {
			t.Fatalf("batch item lost: %#v", item)
		}
	}
}

func TestImprovementValidationReleasesCatalogLock(t *testing.T) {
	invalid := improvementCard("input_uncached_tokens", "a")
	asObject(asObject(asSlice(invalid["components"])[0])["price"])["currency"] = "EUR"
	response := Object{"object": "response", "model": "probe", "usage": Object{"input_tokens": 1, "output_tokens": 0}}
	if value, err := FromResponseAuto(context.Background(), response, Object{"provider": "openai"}, []any{invalid}, nil); err == nil || value != nil {
		t.Fatal("unsupported currency did not return an error")
	}
	done := make(chan error, 1)
	go func() {
		_, err := FromResponseAuto(context.Background(), response, Object{"provider": "openai"}, []any{improvementCard("input_uncached_tokens", "a")}, nil)
		done <- err
	}()
	select {
	case err := <-done:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(time.Second):
		t.Fatal("catalog lock remained held after validation failure")
	}
	for _, policy := range []any{[]any{}, Object{"id": 4, "adjustment": Object{}}, Object{"id": " ", "adjustment": Object{}}, Object{"id": "bad", "adjustment": []any{}}, Object{"id": "bad", "adjustment": Object{"type": 4, "value": "1"}}} {
		if value, err := CalculateCostWithOptionsE(improvementUsage(), []any{improvementCard("input_uncached_tokens", "a")}, []any{policy}, Object{}); err == nil || value != nil {
			t.Fatalf("malformed discount accepted: %#v %v", value, err)
		}
	}
}
