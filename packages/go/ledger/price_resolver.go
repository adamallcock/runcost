package ledger

// This file contains the explicit network/cache convenience layer. The core
// calculation APIs remain deterministic and never call these functions.

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

const DefaultPriceCacheMaxAgeSeconds = 24 * 60 * 60

var DefaultExternalPriceSources = []string{"genai-prices", "models.dev", "litellm"}
var OpenRouterExternalPriceSources = []string{"openrouter", "genai-prices", "models.dev", "litellm"}
var ExternalPriceSourceURLs = map[string]string{
	"genai-prices": "https://raw.githubusercontent.com/pydantic/genai-prices/main/prices/data_slim.json",
	"models.dev":   "https://models.dev/api.json",
	"litellm":      "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
	"openrouter":   "https://openrouter.ai/api/v1/models",
}

var incompletePriceWarningCodes = map[string]bool{
	"unknown_provider": true, "unknown_model": true, "price_not_found": true,
	"component_unpriced": true, "tool_component_unpriced": true,
	"source_capability_unsupported": true, "service_tier_unsupported": true,
	"long_context_rule_missing": true, "historical_price_missing": true,
	"pricing_period_required": true, "pricing_period_unsupported": true,
	"billing_schedule_unsupported": true,
}

type resolverCacheMemoEntry struct {
	modified int64
	size     int64
	cache    Object
}

type resolverCatalogMemoEntry struct {
	cards   []any
	catalog *CompiledPriceCatalog
}

var resolverMemo = struct {
	sync.RWMutex
	files    map[string]resolverCacheMemoEntry
	catalogs map[string]resolverCatalogMemoEntry
}{files: map[string]resolverCacheMemoEntry{}, catalogs: map[string]resolverCatalogMemoEntry{}}

// DefaultPriceCacheDir returns the OS user-cache location for external prices.
func DefaultPriceCacheDir() string {
	if value := os.Getenv("RUNCOST_PRICE_CACHE_DIR"); value != "" {
		return value
	}
	root, err := os.UserCacheDir()
	if err != nil || root == "" {
		root = filepath.Join(".", ".runcost-cache")
	}
	return filepath.Join(root, "runcost", "prices")
}

func resolverNow(value any) (time.Time, error) {
	switch typed := value.(type) {
	case nil:
		return time.Now().UTC(), nil
	case time.Time:
		return typed.UTC(), nil
	case string:
		parsed, err := time.Parse(time.RFC3339, typed)
		if err != nil {
			return time.Time{}, fmt.Errorf("now must be an RFC3339 timestamp: %w", err)
		}
		return parsed.UTC(), nil
	default:
		return time.Time{}, errors.New("now must be an RFC3339 timestamp, time.Time, or nil")
	}
}

func resolverTimestamp(value time.Time) string {
	return value.UTC().Truncate(time.Second).Format(time.RFC3339)
}

func resolverChecksum(value []byte) string {
	digest := sha256.Sum256(value)
	return "sha256:" + hex.EncodeToString(digest[:])
}

func resolverCacheKey(source, sourceURL string) string {
	digest := sha256.Sum256([]byte(sourceURL))
	safe := strings.Map(func(character rune) rune {
		if character >= 'a' && character <= 'z' || character >= 'A' && character <= 'Z' || character >= '0' && character <= '9' || strings.ContainsRune("-.", character) {
			return character
		}
		return '-'
	}, source)
	return fmt.Sprintf("%s-%s.json", safe, hex.EncodeToString(digest[:])[:12])
}

func decodeResolverJSON(value []byte) (any, error) {
	decoder := json.NewDecoder(bytes.NewReader(value))
	decoder.UseNumber()
	var result any
	if err := decoder.Decode(&result); err != nil {
		return nil, err
	}
	return result, nil
}

func readResolverCache(cacheDir, source, sourceURL string) (Object, string) {
	cacheKey := resolverCacheKey(source, sourceURL)
	cachePath := filepath.Join(cacheDir, cacheKey)
	stat, err := os.Stat(cachePath)
	if err != nil {
		resolverMemo.Lock()
		delete(resolverMemo.files, cachePath)
		resolverMemo.Unlock()
		return nil, cacheKey
	}
	resolverMemo.RLock()
	memoized, found := resolverMemo.files[cachePath]
	resolverMemo.RUnlock()
	if found && memoized.modified == stat.ModTime().UnixNano() && memoized.size == stat.Size() {
		return memoized.cache, cacheKey
	}
	encoded, err := os.ReadFile(cachePath)
	if err != nil {
		return nil, cacheKey
	}
	decoded, err := decodeResolverJSON(encoded)
	if err != nil {
		return nil, cacheKey
	}
	cache := asObject(decoded)
	metadata := asObject(cache["source"])
	cards := asSlice(cache["price_cards"])
	if asString(cache["schema_version"]) != "0.1" || asString(metadata["name"]) != source || asString(metadata["url"]) != sourceURL || cards == nil {
		return nil, cacheKey
	}
	if expected := asString(cache["cards_checksum"]); expected != "" && expected != resolverChecksum(CanonicalJSONBytes(cards)) {
		return nil, cacheKey
	}
	resolverMemo.Lock()
	resolverMemo.files[cachePath] = resolverCacheMemoEntry{modified: stat.ModTime().UnixNano(), size: stat.Size(), cache: cache}
	resolverMemo.Unlock()
	return cache, cacheKey
}

func atomicWriteResolverCache(cacheDir, cacheKey string, value Object) error {
	if err := os.MkdirAll(cacheDir, 0o700); err != nil {
		return err
	}
	file, err := os.CreateTemp(cacheDir, "."+cacheKey+".*.tmp")
	if err != nil {
		return err
	}
	name := file.Name()
	defer os.Remove(name)
	if err := file.Chmod(0o600); err != nil {
		file.Close()
		return err
	}
	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(value); err != nil {
		file.Close()
		return err
	}
	if err := file.Sync(); err != nil {
		file.Close()
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	destination := filepath.Join(cacheDir, cacheKey)
	if err := os.Rename(name, destination); err != nil {
		return err
	}
	stat, err := os.Stat(destination)
	if err != nil {
		return err
	}
	resolverMemo.Lock()
	resolverMemo.files[destination] = resolverCacheMemoEntry{modified: stat.ModTime().UnixNano(), size: stat.Size(), cache: value}
	resolverMemo.Unlock()
	return nil
}

func compiledResolverCatalog(cards []any) *CompiledPriceCatalog {
	if len(cards) == 0 {
		return CompilePriceCatalog(cards)
	}
	key := fmt.Sprintf("%p:%d", &cards[0], len(cards))
	resolverMemo.RLock()
	memoized, found := resolverMemo.catalogs[key]
	resolverMemo.RUnlock()
	if found && len(memoized.cards) == len(cards) && &memoized.cards[0] == &cards[0] {
		return memoized.catalog
	}
	compiled := CompilePriceCatalog(cards)
	resolverMemo.Lock()
	if len(resolverMemo.catalogs) >= 32 {
		resolverMemo.catalogs = map[string]resolverCatalogMemoEntry{}
	}
	resolverMemo.catalogs[key] = resolverCatalogMemoEntry{cards: cards, catalog: compiled}
	resolverMemo.Unlock()
	return compiled
}

func resolverCacheAge(cache Object, now time.Time) (float64, bool) {
	metadata := asObject(cache["source"])
	value := asString(firstNonNil(metadata["validated_at"], metadata["retrieved_at"]))
	parsed, err := time.Parse(time.RFC3339, value)
	if err != nil {
		return 0, false
	}
	age := now.Sub(parsed).Seconds()
	if age < 0 {
		age = 0
	}
	return age, true
}

func resolverSafeURL(value string) bool {
	parsed, err := url.Parse(value)
	if err != nil || parsed.Hostname() == "" {
		return false
	}
	if parsed.Scheme == "https" {
		return true
	}
	return parsed.Scheme == "http" && (parsed.Hostname() == "localhost" || net.ParseIP(parsed.Hostname()).IsLoopback())
}

func resolverHTTPClient(options Object) *http.Client {
	if client, ok := options["http_client"].(*http.Client); ok && client != nil {
		return client
	}
	timeout := 15 * time.Second
	if value := firstNonNil(options["timeout_seconds"], options["timeoutSeconds"]); value != nil {
		if parsed, err := time.ParseDuration(fmt.Sprintf("%ss", value)); err == nil && parsed > 0 {
			timeout = parsed
		}
	}
	return &http.Client{
		Timeout: timeout,
		CheckRedirect: func(request *http.Request, _ []*http.Request) error {
			if !resolverSafeURL(request.URL.String()) {
				return errors.New("price source redirected to an unsupported URL")
			}
			return nil
		},
	}
}

func fetchResolverSource(ctx context.Context, sourceURL string, headers Object, options Object) (int, http.Header, []byte, string, error) {
	if !resolverSafeURL(sourceURL) {
		return 0, nil, nil, "", errors.New("price source URL must use HTTPS (loopback HTTP is allowed for tests)")
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, sourceURL, nil)
	if err != nil {
		return 0, nil, nil, "", err
	}
	request.Header.Set("Accept", "application/json")
	request.Header.Set("User-Agent", "runcost-price-resolver/0.2")
	for key, value := range headers {
		request.Header.Set(key, asString(value))
	}
	response, err := resolverHTTPClient(options).Do(request)
	if err != nil {
		return 0, nil, nil, "", err
	}
	defer response.Body.Close()
	maxBytes := int64(64 * 1024 * 1024)
	if value := firstNonNil(options["max_bytes"], options["maxBytes"]); value != nil {
		if parsed, err := fmt.Sscan(fmt.Sprint(value), &maxBytes); parsed != 1 || err != nil || maxBytes <= 0 {
			return 0, nil, nil, "", errors.New("max_bytes must be a positive integer")
		}
	}
	if response.StatusCode == http.StatusNotModified {
		return response.StatusCode, response.Header, nil, response.Request.URL.String(), nil
	}
	body, err := io.ReadAll(io.LimitReader(response.Body, maxBytes+1))
	if err != nil {
		return 0, nil, nil, "", err
	}
	if int64(len(body)) > maxBytes {
		return 0, nil, nil, "", fmt.Errorf("price source exceeds the %d-byte safety limit", maxBytes)
	}
	return response.StatusCode, response.Header, body, response.Request.URL.String(), nil
}

func adaptExternalPriceSource(source string, payload any, sourceURL, retrievedAt string) []any {
	var cards []any
	switch source {
	case "genai-prices":
		cards = PriceCardsFromGenAIPrices(payload, Object{"retrieved_at": retrievedAt})
	case "models.dev":
		cards = PriceCardsFromModelsDev(asObject(payload))
	case "litellm":
		cards = PriceCardsFromLiteLLM(asObject(payload))
	case "openrouter":
		cards = PriceCardsFromOpenRouterModels(asObject(payload))
	default:
		return nil
	}
	for _, rawCard := range cards {
		asObject(rawCard)["source"] = Object{"name": source, "url": sourceURL, "retrieved_at": retrievedAt}
	}
	return cards
}

func resolverSourceWarning(code, source, status string) Object {
	message := fmt.Sprintf("External price source %s is unavailable and has no usable cache.", source)
	if code == "price_source_refresh_failed" {
		message = fmt.Sprintf("Could not refresh external price source %s; using its last-known-good cache.", source)
	}
	return Object{"code": code, "message": message, "metadata": Object{"source": source, "status": status}}
}

func resolveExternalSourceState(ctx context.Context, source, sourceURL, cacheDir string, now time.Time, options Object) (Object, []any) {
	cache, cacheKey := readResolverCache(cacheDir, source, sourceURL)
	state := Object{"name": source, "type": "external", "url": sourceURL, "cache_key": cacheKey, "status": "unavailable", "card_count": 0}
	if cache != nil {
		metadata := asObject(cache["source"])
		state["card_count"] = len(asSlice(cache["price_cards"]))
		for _, key := range []string{"retrieved_at", "validated_at", "checksum", "etag", "last_modified"} {
			if metadata[key] != nil && asString(metadata[key]) != "" {
				state[key] = metadata[key]
			}
		}
	}
	maxAge := float64(DefaultPriceCacheMaxAgeSeconds)
	if value := firstNonNil(options["max_age_seconds"], options["maxAgeSeconds"]); value != nil {
		if _, err := fmt.Sscan(fmt.Sprint(value), &maxAge); err != nil || maxAge < 0 {
			return state, []any{resolverSourceWarning("price_source_unavailable", source, "invalid_max_age")}
		}
	}
	offline, _ := optionalBool(options["offline"])
	refresh, _ := optionalBool(options["refresh"])
	age, hasAge := resolverCacheAge(cache, now)
	if offline {
		if cache != nil {
			state["status"] = "cache_stale"
			if hasAge && age <= maxAge {
				state["status"] = "cache_fresh"
			}
			state["price_cards"] = asSlice(cache["price_cards"])
			return state, nil
		}
		return state, []any{resolverSourceWarning("price_source_unavailable", source, "offline_cache_miss")}
	}
	if cache != nil && !refresh && hasAge && age <= maxAge {
		state["status"] = "cache_fresh"
		state["price_cards"] = asSlice(cache["price_cards"])
		return state, nil
	}
	headers := Object{}
	if cache != nil {
		metadata := asObject(cache["source"])
		if value := asString(metadata["etag"]); value != "" {
			headers["If-None-Match"] = value
		}
		if value := asString(metadata["last_modified"]); value != "" {
			headers["If-Modified-Since"] = value
		}
	}
	status, responseHeaders, body, finalURL, err := fetchResolverSource(ctx, sourceURL, headers, options)
	checkedAt := resolverTimestamp(now)
	if err == nil && status == http.StatusNotModified && cache != nil {
		metadata := asObject(cache["source"])
		metadata["validated_at"] = checkedAt
		if value := responseHeaders.Get("ETag"); value != "" {
			metadata["etag"] = value
		}
		if value := responseHeaders.Get("Last-Modified"); value != "" {
			metadata["last_modified"] = value
		}
		if writeErr := atomicWriteResolverCache(cacheDir, cacheKey, cache); writeErr != nil {
			err = writeErr
		} else {
			state["status"] = "cache_validated"
			state["validated_at"] = checkedAt
			state["price_cards"] = asSlice(cache["price_cards"])
			return state, nil
		}
	}
	if err == nil && status >= 200 && status < 300 {
		payload, decodeErr := decodeResolverJSON(body)
		if decodeErr == nil {
			cards := adaptExternalPriceSource(source, payload, finalURL, checkedAt)
			if len(cards) > 0 {
				metadata := Object{"name": source, "type": "external", "url": sourceURL, "resolved_url": finalURL, "retrieved_at": checkedAt, "validated_at": checkedAt, "checksum": resolverChecksum(body)}
				if value := responseHeaders.Get("ETag"); value != "" {
					metadata["etag"] = value
				}
				if value := responseHeaders.Get("Last-Modified"); value != "" {
					metadata["last_modified"] = value
				}
				envelope := Object{"schema_version": "0.1", "source": metadata, "cards_checksum": resolverChecksum(CanonicalJSONBytes(cards)), "price_cards": cards}
				if writeErr := atomicWriteResolverCache(cacheDir, cacheKey, envelope); writeErr == nil {
					state["status"] = "refreshed"
					state["retrieved_at"] = checkedAt
					state["validated_at"] = checkedAt
					state["checksum"] = metadata["checksum"]
					state["card_count"] = len(cards)
					state["price_cards"] = cards
					return state, nil
				} else {
					err = writeErr
				}
			} else {
				err = errors.New("price source produced no supported price cards")
			}
		} else {
			err = decodeErr
		}
	} else if err == nil {
		err = fmt.Errorf("price source returned HTTP %d", status)
	}
	if cache != nil {
		state["status"] = "cache_stale"
		state["price_cards"] = asSlice(cache["price_cards"])
		return state, []any{resolverSourceWarning("price_source_refresh_failed", source, "last_known_good")}
	}
	return state, []any{resolverSourceWarning("price_source_unavailable", source, "fetch_failed")}
}

func resolverStringSlice(value any) []string {
	result := []string{}
	for _, item := range asSlice(value) {
		result = append(result, asString(item))
	}
	return result
}

func resolverSourceOrder(provider string, requested any) ([]string, error) {
	var sources []string
	if requested != nil {
		sources = resolverStringSlice(requested)
	} else if strings.EqualFold(provider, "openrouter") {
		sources = append([]string{}, OpenRouterExternalPriceSources...)
	} else {
		sources = append([]string{}, DefaultExternalPriceSources...)
	}
	result := []string{}
	seen := map[string]bool{}
	for _, source := range sources {
		if ExternalPriceSourceURLs[source] == "" {
			return nil, fmt.Errorf("unsupported external price source: %s", source)
		}
		if !seen[source] {
			seen[source] = true
			result = append(result, source)
		}
	}
	if len(result) == 0 {
		return nil, errors.New("at least one external price source is required")
	}
	return result, nil
}

func externalCandidateQuality(usage Object, cards []any) (complete bool, priced int) {
	defer func() {
		if recover() != nil {
			complete = false
			priced = 0
		}
	}()
	ledger := calculateCostWithCompiledOptions(usage, compiledResolverCatalog(cards), nil, Object{"mode": "compatibility"})
	for _, rawWarning := range asSlice(ledger["warnings"]) {
		if incompletePriceWarningCodes[asString(asObject(rawWarning)["code"])] {
			return false, len(asSlice(ledger["components"]))
		}
	}
	return true, len(asSlice(ledger["components"]))
}

// ResolvePriceCatalog selects exactly one external source and never merges cards.
func ResolvePriceCatalog(ctx context.Context, options Object) (Object, error) {
	if options == nil {
		options = Object{}
	}
	now, err := resolverNow(options["now"])
	if err != nil {
		return nil, err
	}
	var explicit []any
	explicitProvided := false
	for _, key := range []string{"contract_price_cards", "contractPriceCards", "price_cards", "priceCards"} {
		if value, exists := options[key]; exists && value != nil {
			explicit = asSlice(value)
			explicitProvided = true
			break
		}
	}
	if explicitProvided {
		typeName := "user"
		if options["contract_price_cards"] != nil || options["contractPriceCards"] != nil {
			typeName = "contract"
		}
		return Object{
			"schema_version": "0.1", "selected_source": "user", "price_cards": explicit,
			"sources":  []any{Object{"name": "user", "type": typeName, "status": "selected", "card_count": len(explicit)}},
			"warnings": []any{}, "resolved_at": resolverTimestamp(now),
		}, nil
	}
	usage := asObject(firstNonNil(options["usage_ledger"], options["usageLedger"]))
	provider := asString(firstNonNil(options["provider"], usage["provider"]))
	sources, err := resolverSourceOrder(provider, firstNonNil(options["sources"], options["price_sources"], options["priceSources"]))
	if err != nil {
		return nil, err
	}
	urls := map[string]string{}
	for key, value := range ExternalPriceSourceURLs {
		urls[key] = value
	}
	if overrides, ok := objectValue(firstNonNil(options["source_urls"], options["sourceUrls"])); ok {
		for key, value := range overrides {
			urls[key] = asString(value)
		}
	}
	cacheDir := asString(firstNonNil(options["cache_dir"], options["cacheDir"]))
	if cacheDir == "" {
		cacheDir = DefaultPriceCacheDir()
	}
	states := []any{}
	warnings := []any{}
	var firstPartial Object
	var selected Object
	for _, source := range sources {
		state, sourceWarnings := resolveExternalSourceState(ctx, source, urls[source], cacheDir, now, options)
		cards := asSlice(state["price_cards"])
		delete(state, "price_cards")
		states = append(states, state)
		warnings = append(warnings, sourceWarnings...)
		if len(cards) == 0 {
			continue
		}
		if len(usage) == 0 {
			selected = Object{"source": source, "cards": cards}
			break
		}
		complete, priced := externalCandidateQuality(usage, cards)
		state["priced_component_count"] = priced
		state["applicable"] = priced > 0
		if priced > 0 && firstPartial == nil {
			firstPartial = Object{"source": source, "cards": cards}
		}
		if complete {
			selected = Object{"source": source, "cards": cards}
			break
		}
	}
	if selected == nil {
		selected = firstPartial
	}
	selectedSource := asString(selected["source"])
	for _, rawState := range states {
		state := asObject(rawState)
		state["selected"] = asString(state["name"]) == selectedSource
	}
	if selected == nil {
		warnings = append(warnings, Object{"code": "price_source_unavailable", "message": "No configured external price source produced applicable price cards.", "metadata": Object{"source": strings.Join(sources, ","), "status": "no_applicable_source"}})
	}
	deduplicated := []any{}
	seenWarnings := map[string]bool{}
	for _, rawWarning := range warnings {
		warning := asObject(rawWarning)
		metadata := asObject(warning["metadata"])
		key := asString(warning["code"]) + "\x00" + asString(metadata["source"]) + "\x00" + asString(metadata["status"])
		if !seenWarnings[key] {
			seenWarnings[key] = true
			deduplicated = append(deduplicated, warning)
		}
	}
	return Object{
		"schema_version": "0.1", "selected_source": firstNonNil(selected["source"], nil),
		"price_cards": asSlice(selected["cards"]), "sources": states, "warnings": deduplicated,
		"resolved_at": resolverTimestamp(now),
	}, nil
}

func resolverMetadata(resolution Object) Object {
	return Object{"schema_version": firstNonNil(resolution["schema_version"], "0.1"), "selected_source": resolution["selected_source"], "sources": resolution["sources"], "resolved_at": resolution["resolved_at"]}
}

// AttachPriceResolution adds audit provenance and operational warnings.
func AttachPriceResolution(result, resolution Object) Object {
	metadata := cloneObject(asObject(result["metadata"]))
	metadata["price_resolution"] = resolverMetadata(resolution)
	result["metadata"] = metadata
	warnings := append([]any{}, asSlice(result["warnings"])...)
	seen := map[string]bool{}
	for _, rawWarning := range warnings {
		warning := asObject(rawWarning)
		seen[asString(warning["code"])+"\x00"+string(CanonicalJSONBytes(warning["metadata"]))] = true
	}
	for _, rawWarning := range asSlice(resolution["warnings"]) {
		warning := asObject(rawWarning)
		key := asString(warning["code"]) + "\x00" + string(CanonicalJSONBytes(warning["metadata"]))
		if !seen[key] {
			warnings = append(warnings, warning)
			seen[key] = true
		}
	}
	result["warnings"] = warnings
	return result
}

var resolverOptionNames = map[string]bool{
	"contract_price_cards": true, "contractPriceCards": true, "sources": true,
	"price_sources": true, "priceSources": true, "source_urls": true, "sourceUrls": true,
	"cache_dir": true, "cacheDir": true, "offline": true, "refresh": true,
	"max_age_seconds": true, "maxAgeSeconds": true, "timeout_seconds": true,
	"timeoutSeconds": true, "max_bytes": true, "maxBytes": true, "http_client": true,
	"now": true,
}

func splitResolverOptions(options Object) (Object, Object) {
	calculation := Object{}
	resolver := Object{}
	for key, value := range options {
		if resolverOptionNames[key] {
			resolver[key] = value
		} else {
			calculation[key] = value
		}
	}
	return calculation, resolver
}

func tryExtractAutoUsage(response Object, options Object) (usage Object, ok bool) {
	defer func() {
		if recover() != nil {
			usage = nil
			ok = false
		}
	}()
	if asString(options["surface"]) == "" {
		options["surface"] = InferSurface(response, asString(options["provider"]))
	}
	if asString(options["surface"]) == "" {
		return nil, false
	}
	return ExtractUsageLedger(response, options), true
}

// FromResponseAuto resolves external prices before calling deterministic FromResponse.
func FromResponseAuto(ctx context.Context, response Object, options Object, priceCards []any, discountPolicies []any) (Object, error) {
	calculation, resolver := splitResolverOptions(cloneObject(options))
	if priceCards != nil {
		resolver["price_cards"] = priceCards
	}
	usage, ok := tryExtractAutoUsage(response, cloneObject(calculation))
	if ok {
		resolver["usage_ledger"] = usage
		resolver["provider"] = usage["provider"]
	}
	resolution, err := ResolvePriceCatalog(ctx, resolver)
	if err != nil {
		return nil, err
	}
	cards := asSlice(resolution["price_cards"])
	result := fromResponseWithCatalog(response, calculation, cards, discountPolicies, compiledResolverCatalog(cards))
	return AttachPriceResolution(result, resolution), nil
}

// FromBatchResultsAuto resolves one source for an entire provider batch.
func FromBatchResultsAuto(ctx context.Context, items []any, options Object) (Object, error) {
	calculation, resolver := splitResolverOptions(cloneObject(options))
	resolver["provider"] = calculation["provider"]
	if value := firstNonNil(calculation["price_cards"], calculation["priceCards"]); value != nil {
		resolver["price_cards"] = value
	}
	delete(calculation, "price_cards")
	delete(calculation, "priceCards")
	resolution, err := ResolvePriceCatalog(ctx, resolver)
	if err != nil {
		return nil, err
	}
	calculation["price_cards"] = resolution["price_cards"]
	result := FromBatchResults(items, calculation)
	metadata := cloneObject(asObject(result["metadata"]))
	metadata["price_resolution"] = resolverMetadata(resolution)
	result["metadata"] = metadata
	if aggregate := asObject(result["aggregate"]); aggregate != nil {
		result["aggregate"] = AttachPriceResolution(aggregate, resolution)
	}
	for _, rawItem := range asSlice(result["items"]) {
		item := asObject(rawItem)
		if item["ledger"] != nil {
			item["ledger"] = AttachPriceResolution(asObject(item["ledger"]), resolution)
		}
	}
	shadow := Object{"warnings": result["warnings"], "metadata": result["metadata"]}
	AttachPriceResolution(shadow, resolution)
	result["warnings"] = shadow["warnings"]
	return result, nil
}

// FromOTelGenAISpanAuto resolves external prices for a GenAI telemetry span.
func FromOTelGenAISpanAuto(ctx context.Context, span, options Object, priceCards []any, discountPolicies []any) (Object, error) {
	calculation, resolver := splitResolverOptions(cloneObject(options))
	usage := UsageLedgerFromOTelGenAISpan(span, calculation)
	resolver["usage_ledger"] = usage
	resolver["provider"] = usage["provider"]
	if priceCards != nil {
		resolver["price_cards"] = priceCards
	}
	resolution, err := ResolvePriceCatalog(ctx, resolver)
	if err != nil {
		return nil, err
	}
	result := FromOTelGenAISpan(span, calculation, asSlice(resolution["price_cards"]), discountPolicies)
	return AttachPriceResolution(result, resolution), nil
}

// EstimateCostAuto resolves external prices for a pre-call estimate.
func EstimateCostAuto(ctx context.Context, options Object, priceCards []any, discountPolicies []any) (Object, error) {
	calculation, resolver := splitResolverOptions(cloneObject(options))
	components := []any{}
	if raw, ok := calculation["components"].([]any); ok {
		components = raw
	} else if raw, ok := objectValue(calculation["components"]); ok {
		for key, value := range raw {
			components = append(components, Object{"name": key, "quantity": fmt.Sprint(value), "unit": "token"})
		}
	}
	model := asString(calculation["model"])
	usage := Object{"schema_version": "0.1", "provider": calculation["provider"], "surface": calculation["surface"], "model": Object{"requested": model, "returned": model, "billed": model, "alias_resolution": "none"}, "components": components}
	if calculation["context"] != nil {
		usage["context"] = calculation["context"]
	}
	resolver["usage_ledger"] = usage
	resolver["provider"] = calculation["provider"]
	if priceCards != nil {
		resolver["price_cards"] = priceCards
	}
	resolution, err := ResolvePriceCatalog(ctx, resolver)
	if err != nil {
		return nil, err
	}
	result := EstimateCost(calculation, asSlice(resolution["price_cards"]), discountPolicies)
	return AttachPriceResolution(result, resolution), nil
}

// PriceCacheStatus inspects cache metadata without returning price payloads.
func PriceCacheStatus(options Object) (Object, error) {
	cacheDir := asString(firstNonNil(options["cache_dir"], options["cacheDir"]))
	if cacheDir == "" {
		cacheDir = DefaultPriceCacheDir()
	}
	now, err := resolverNow(options["now"])
	if err != nil {
		return nil, err
	}
	entries := []any{}
	files, err := os.ReadDir(cacheDir)
	if err != nil && !os.IsNotExist(err) {
		return nil, err
	}
	for _, file := range files {
		if file.IsDir() || !strings.HasSuffix(file.Name(), ".json") {
			continue
		}
		encoded, readErr := os.ReadFile(filepath.Join(cacheDir, file.Name()))
		if readErr != nil {
			entries = append(entries, Object{"cache_key": file.Name(), "status": "invalid"})
			continue
		}
		decoded, decodeErr := decodeResolverJSON(encoded)
		if decodeErr != nil {
			entries = append(entries, Object{"cache_key": file.Name(), "status": "invalid"})
			continue
		}
		cache := asObject(decoded)
		metadata := asObject(cache["source"])
		entry := Object{"cache_key": file.Name(), "name": metadata["name"], "url": metadata["url"], "retrieved_at": metadata["retrieved_at"], "validated_at": metadata["validated_at"], "checksum": metadata["checksum"], "etag": metadata["etag"], "last_modified": metadata["last_modified"], "card_count": len(asSlice(cache["price_cards"])), "status": "valid"}
		if age, ok := resolverCacheAge(cache, now); ok {
			entry["age_seconds"] = int64(age)
		}
		entries = append(entries, entry)
	}
	sort.Slice(entries, func(left, right int) bool {
		return asString(asObject(entries[left])["cache_key"]) < asString(asObject(entries[right])["cache_key"])
	})
	return Object{"schema_version": "0.1", "cache_dir": cacheDir, "checked_at": resolverTimestamp(now), "entries": entries}, nil
}

// ClearPriceCache removes only RunCost-managed JSON cache entries.
func ClearPriceCache(options Object) (Object, error) {
	cacheDir := asString(firstNonNil(options["cache_dir"], options["cacheDir"]))
	if cacheDir == "" {
		cacheDir = DefaultPriceCacheDir()
	}
	requested := map[string]bool{}
	for _, source := range resolverStringSlice(options["sources"]) {
		requested[source] = true
	}
	removed := []any{}
	files, err := os.ReadDir(cacheDir)
	if err != nil {
		if os.IsNotExist(err) {
			return Object{"schema_version": "0.1", "cache_dir": cacheDir, "removed": removed}, nil
		}
		return nil, err
	}
	for _, file := range files {
		if file.IsDir() || !strings.HasSuffix(file.Name(), ".json") {
			continue
		}
		source := strings.TrimSuffix(file.Name(), ".json")
		if index := strings.LastIndex(source, "-"); index >= 0 {
			source = source[:index]
		}
		if len(requested) > 0 && !requested[source] {
			continue
		}
		if err := os.Remove(filepath.Join(cacheDir, file.Name())); err != nil {
			return nil, err
		}
		resolverMemo.Lock()
		delete(resolverMemo.files, filepath.Join(cacheDir, file.Name()))
		resolverMemo.Unlock()
		removed = append(removed, file.Name())
	}
	return Object{"schema_version": "0.1", "cache_dir": cacheDir, "removed": removed}, nil
}
