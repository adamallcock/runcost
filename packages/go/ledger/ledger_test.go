package ledger

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"
)

func decodeFile(t *testing.T, path string) Object {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	var decoded Object
	if err := decoder.Decode(&decoded); err != nil {
		t.Fatal(err)
	}
	return decoded
}

func allObjects(values []any) bool {
	for _, value := range values {
		if _, ok := value.(map[string]any); !ok {
			return false
		}
	}
	return true
}

func assertSubset(t *testing.T, actual any, expected any, path string) {
	t.Helper()
	switch expectedTyped := expected.(type) {
	case map[string]any:
		actualTyped, ok := actual.(map[string]any)
		if !ok {
			t.Fatalf("%s: expected object, got %T", path, actual)
		}
		for key, expectedValue := range expectedTyped {
			actualValue, ok := actualTyped[key]
			if !ok {
				t.Fatalf("%s.%s: missing", path, key)
			}
			assertSubset(t, actualValue, expectedValue, path+"."+key)
		}
	case []any:
		if allObjects(expectedTyped) {
			actualTyped, ok := actual.([]any)
			if !ok {
				t.Fatalf("%s: expected array, got %T", path, actual)
			}
			if len(actualTyped) != len(expectedTyped) {
				t.Fatalf("%s: expected %d items, got %d", path, len(expectedTyped), len(actualTyped))
			}
			for index, expectedValue := range expectedTyped {
				assertSubset(t, actualTyped[index], expectedValue, fmt.Sprintf("%s[%d]", path, index))
			}
			return
		}
		if !reflect.DeepEqual(actual, expected) {
			t.Fatalf("%s: expected %#v, got %#v", path, expected, actual)
		}
	case json.Number:
		expectedNumber, ok := new(big.Rat).SetString(expectedTyped.String())
		if !ok {
			t.Fatalf("%s: invalid expected number %q", path, expectedTyped.String())
		}
		actualNumber, ok := new(big.Rat).SetString(numberString(actual))
		if !ok {
			t.Fatalf("%s: expected number %q, got non-number %#v", path, expectedTyped.String(), actual)
		}
		if expectedNumber.Cmp(actualNumber) != 0 {
			t.Fatalf("%s: expected %s, got %s", path, expectedNumber.String(), actualNumber.String())
		}
	default:
		if !reflect.DeepEqual(actual, expected) {
			t.Fatalf("%s: expected %#v, got %#v", path, expected, actual)
		}
	}
}

func assertAllowedKeys(t *testing.T, object Object, allowed map[string]bool, path string) {
	t.Helper()
	for key := range object {
		if !allowed[key] {
			t.Fatalf("%s: unexpected property %q", path, key)
		}
	}
}

func requireObject(t *testing.T, value any, path string) Object {
	t.Helper()
	object, ok := value.(map[string]any)
	if !ok {
		t.Fatalf("%s: expected object, got %T", path, value)
	}
	return object
}

func requireSlice(t *testing.T, value any, path string) []any {
	t.Helper()
	slice, ok := value.([]any)
	if !ok {
		t.Fatalf("%s: expected array, got %T", path, value)
	}
	return slice
}

func requireString(t *testing.T, value any, path string) string {
	t.Helper()
	text, ok := value.(string)
	if !ok {
		t.Fatalf("%s: expected string, got %T", path, value)
	}
	if text == "" {
		t.Fatalf("%s: must not be empty", path)
	}
	return text
}

func requireOptionalString(t *testing.T, value any, path string) {
	t.Helper()
	if value == nil {
		return
	}
	if _, ok := value.(string); !ok {
		t.Fatalf("%s: expected string, got %T", path, value)
	}
}

func requireOptionalBool(t *testing.T, value any, path string) {
	t.Helper()
	if value == nil {
		return
	}
	if _, ok := value.(bool); !ok {
		t.Fatalf("%s: expected boolean, got %T", path, value)
	}
}

func requireDecimal(t *testing.T, value any, path string) *big.Rat {
	t.Helper()
	parsed, ok := new(big.Rat).SetString(numberString(value))
	if !ok {
		t.Fatalf("%s: invalid decimal %q", path, numberString(value))
	}
	return parsed
}

func orderedKeys(values []any, key func(Object) string) []string {
	keys := []string{}
	for _, value := range values {
		keys = append(keys, key(asObject(value)))
	}
	return keys
}

func assertOrdered(t *testing.T, values []any, key func(Object) string, path string) {
	t.Helper()
	keys := orderedKeys(values, key)
	expected := append([]string{}, keys...)
	sort.Strings(expected)
	if !reflect.DeepEqual(keys, expected) {
		t.Fatalf("%s: output order is not byte-stable", path)
	}
}

func componentOrderKey(component Object) string {
	return fmt.Sprintf(
		"%04d|%s|%s|%s|%s|%s|%s",
		componentRank(asString(component["name"])),
		asString(component["name"]),
		asString(component["unit"]),
		asString(component["unit_price"]),
		asString(component["price_card_id"]),
		numberString(component["quantity"]),
		numberString(component["cost"]),
	)
}

func sourceOrderKey(source Object) string {
	return sourceKey(source)
}

func discountOrderKey(discount Object) string {
	return strings.Join([]string{
		asString(discount["component"]),
		asString(discount["policy_id"]),
		numberString(discount["amount"]),
	}, "|")
}

func warningOrderKey(warning Object) string {
	metadata, _ := json.Marshal(warning["metadata"])
	return strings.Join([]string{
		asString(warning["code"]),
		asString(warning["path"]),
		asString(warning["message"]),
		string(metadata),
	}, "|")
}

func warningMetadataRequiredKeys(t *testing.T) map[string][]string {
	t.Helper()
	taxonomy := decodeFile(t, "../../../schemas/taxonomy.json")
	rawKeys := requireObject(t, taxonomy["warning_metadata_required_keys"], "taxonomy.warning_metadata_required_keys")
	result := map[string][]string{}
	for code, rawValue := range rawKeys {
		keys := []string{}
		for index, rawKey := range requireSlice(t, rawValue, fmt.Sprintf("taxonomy.warning_metadata_required_keys.%s", code)) {
			keys = append(keys, requireString(t, rawKey, fmt.Sprintf("taxonomy.warning_metadata_required_keys.%s[%d]", code, index)))
		}
		result[code] = keys
	}
	return result
}

func validateCostLedger(t *testing.T, ledger Object, path string, warningMetadataKeys map[string][]string) {
	t.Helper()
	assertAllowedKeys(t, ledger, map[string]bool{
		"schema_version":    true,
		"provider":          true,
		"surface":           true,
		"model":             true,
		"currency":          true,
		"components":        true,
		"total":             true,
		"price_sources":     true,
		"applied_discounts": true,
		"warnings":          true,
		"debug_trace":       true,
		"metadata":          true,
	}, path)
	if requireString(t, ledger["schema_version"], path+".schema_version") != "0.1" {
		t.Fatalf("%s.schema_version: expected 0.1", path)
	}
	requireString(t, ledger["provider"], path+".provider")
	requireString(t, ledger["surface"], path+".surface")
	requireString(t, ledger["currency"], path+".currency")
	requireDecimal(t, ledger["total"], path+".total")

	model := requireObject(t, ledger["model"], path+".model")
	assertAllowedKeys(t, model, map[string]bool{
		"requested":        true,
		"returned":         true,
		"billed":           true,
		"alias_resolution": true,
	}, path+".model")
	requireString(t, model["requested"], path+".model.requested")
	requireString(t, model["billed"], path+".model.billed")
	requireOptionalString(t, model["returned"], path+".model.returned")
	requireOptionalString(t, model["alias_resolution"], path+".model.alias_resolution")

	componentTotal := new(big.Rat)
	components := requireSlice(t, ledger["components"], path+".components")
	assertOrdered(t, components, componentOrderKey, path+".components")
	for index, value := range components {
		componentPath := fmt.Sprintf("%s.components[%d]", path, index)
		component := requireObject(t, value, componentPath)
		assertAllowedKeys(t, component, map[string]bool{
			"name":              true,
			"quantity":          true,
			"unit":              true,
			"unit_price":        true,
			"cost":              true,
			"price_card_id":     true,
			"discount_eligible": true,
			"metadata":          true,
		}, componentPath)
		requireString(t, component["name"], componentPath+".name")
		requireDecimal(t, component["quantity"], componentPath+".quantity")
		requireString(t, component["unit"], componentPath+".unit")
		requireDecimal(t, component["unit_price"], componentPath+".unit_price")
		componentTotal.Add(componentTotal, requireDecimal(t, component["cost"], componentPath+".cost"))
		requireOptionalString(t, component["price_card_id"], componentPath+".price_card_id")
		requireOptionalBool(t, component["discount_eligible"], componentPath+".discount_eligible")
		if metadata, ok := component["metadata"]; ok {
			requireObject(t, metadata, componentPath+".metadata")
		}
	}
	if componentTotal.Cmp(requireDecimal(t, ledger["total"], path+".total")) != 0 {
		t.Fatalf("%s: component costs sum to %s, total is %s", path, componentTotal.String(), requireDecimal(t, ledger["total"], path+".total").String())
	}

	priceSources := asSlice(ledger["price_sources"])
	assertOrdered(t, priceSources, sourceOrderKey, path+".price_sources")
	for index, value := range priceSources {
		sourcePath := fmt.Sprintf("%s.price_sources[%d]", path, index)
		source := requireObject(t, value, sourcePath)
		assertAllowedKeys(t, source, map[string]bool{"name": true, "url": true, "retrieved_at": true, "version": true, "license": true}, sourcePath)
		requireString(t, source["name"], sourcePath+".name")
		requireOptionalString(t, source["url"], sourcePath+".url")
		requireOptionalString(t, source["retrieved_at"], sourcePath+".retrieved_at")
		requireOptionalString(t, source["version"], sourcePath+".version")
		requireOptionalString(t, source["license"], sourcePath+".license")
	}
	appliedDiscounts := asSlice(ledger["applied_discounts"])
	assertOrdered(t, appliedDiscounts, discountOrderKey, path+".applied_discounts")
	for index, value := range appliedDiscounts {
		discountPath := fmt.Sprintf("%s.applied_discounts[%d]", path, index)
		discount := requireObject(t, value, discountPath)
		assertAllowedKeys(t, discount, map[string]bool{"policy_id": true, "component": true, "amount": true}, discountPath)
		requireString(t, discount["policy_id"], discountPath+".policy_id")
		requireString(t, discount["component"], discountPath+".component")
		requireDecimal(t, discount["amount"], discountPath+".amount")
	}
	warnings := requireSlice(t, ledger["warnings"], path+".warnings")
	assertOrdered(t, warnings, warningOrderKey, path+".warnings")
	for index, value := range warnings {
		warningPath := fmt.Sprintf("%s.warnings[%d]", path, index)
		warning := requireObject(t, value, warningPath)
		assertAllowedKeys(t, warning, map[string]bool{"code": true, "message": true, "path": true, "metadata": true}, warningPath)
		code := requireString(t, warning["code"], warningPath+".code")
		requireString(t, warning["message"], warningPath+".message")
		requireOptionalString(t, warning["path"], warningPath+".path")
		metadata := requireObject(t, warning["metadata"], warningPath+".metadata")
		for _, key := range warningMetadataKeys[code] {
			if _, ok := metadata[key]; !ok {
				t.Fatalf("%s.metadata.%s: missing required warning metadata", warningPath, key)
			}
		}
	}
	if debugTrace, ok := ledger["debug_trace"]; ok {
		trace := requireObject(t, debugTrace, path+".debug_trace")
		requireString(t, trace["schema_version"], path+".debug_trace.schema_version")
		requireSlice(t, trace["decisions"], path+".debug_trace.decisions")
		requireObject(t, trace["summary"], path+".debug_trace.summary")
	}
	if metadata, ok := ledger["metadata"]; ok {
		requireObject(t, metadata, path+".metadata")
	}
}

func resolvePriceCards(t *testing.T, input Object) []any {
	t.Helper()
	if value, ok := input["price_cards"]; ok {
		return asSlice(value)
	}
	source := asObject(input["price_source"])
	switch asString(source["type"]) {
	case "llm-prices":
		return PriceCardsFromLlmPrices(asObject(source["data"]))
	case "litellm":
		return PriceCardsFromLiteLLM(asObject(source["data"]))
	case "openrouter-models":
		return PriceCardsFromOpenRouterModels(asObject(source["data"]))
	case "models-dev":
		return PriceCardsFromModelsDev(asObject(source["data"]))
	case "official-snapshot":
		return PriceCardsFromOfficialSnapshot(asObject(source["data"]))
	case "portkey":
		return PriceCardsFromPortkey(asObject(source["data"]))
	case "source-cache":
		return PriceCardsFromSourceCache(asObject(source["data"]))
	case "user-pricing":
		return PriceCardsFromUserPricing(asObject(source["data"]))
	case "helicone":
		return PriceCardsFromHelicone(asObject(source["data"]))
	case "json-file":
		path := asString(source["path"])
		if !filepath.IsAbs(path) {
			path = filepath.Join("../../../", path)
		}
		cards, err := PriceCardsFromJSONFile(path, asString(source["source_type"]))
		if err != nil {
			t.Fatal(err)
		}
		return cards
	case "yaml-file":
		path := asString(source["path"])
		if !filepath.IsAbs(path) {
			path = filepath.Join("../../../", path)
		}
		cards, err := PriceCardsFromYAMLFile(path, asString(source["source_type"]))
		if err != nil {
			t.Fatal(err)
		}
		return cards
	default:
		t.Fatalf("unsupported price source: %s", asString(source["type"]))
	}
	return nil
}

func runFixture(t *testing.T, fixture Object) Object {
	t.Helper()
	input := asObject(fixture["input"])
	if value, ok := input["cost_ledgers"]; ok {
		options := asObject(input["options"])
		mode := asString(input["mode"])
		if mode == "" {
			mode = "compatibility"
		}
		options["mode"] = mode
		return AggregateCostLedgers(asSlice(value), options)
	}
	priceCards := resolvePriceCards(t, input)
	discountPolicies := asSlice(input["discount_policies"])
	mode := asString(input["mode"])
	if mode == "" {
		mode = "compatibility"
	}
	options := asObject(input["options"])
	options["mode"] = mode
	if rawResponse, ok := input["raw_response"]; ok {
		extractOptions := asObject(input["extract"])
		for key, value := range options {
			extractOptions[key] = value
		}
		switch asString(input["helper"]) {
		case "from_langchain_message":
			return FromLangChainMessage(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		case "from_vercel_ai_sdk_result":
			return FromVercelAISDKResult(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		case "from_vercel_ai_sdk_stream_finish":
			return FromVercelAISDKStreamFinish(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		case "from_llamaindex_token_counter":
			return FromLlamaIndexTokenCounter(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		case "from_haystack_generator_result":
			return FromHaystackGeneratorResult(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		case "from_litellm_response":
			return FromLiteLLMResponse(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		case "from_ag2_usage_summary":
			return FromAG2UsageSummary(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		case "from_openai_agents_usage":
			return FromOpenAIAgentsUsage(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		case "from_langsmith_run":
			return FromLangSmithRun(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		case "from_semantic_kernel_telemetry":
			return FromSemanticKernelTelemetry(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		case "from_openrouter_sdk_response":
			return FromOpenRouterSDKResponse(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		default:
			return FromResponse(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		}
	}
	return CalculateCostWithOptions(asObject(input["usage_ledger"]), priceCards, discountPolicies, options)
}

func fixtureExpectedLanguages(fixture Object) []any {
	metadata := asObject(fixture["metadata"])
	languages := asSlice(metadata["expected_languages"])
	if len(languages) == 0 {
		return []any{"python", "javascript", "go"}
	}
	return languages
}

func TestFixtures(t *testing.T) {
	paths, err := filepath.Glob("../../../fixtures/*.json")
	if err != nil {
		t.Fatal(err)
	}
	if len(paths) == 0 {
		t.Fatal("no fixtures found")
	}
	warningMetadataKeys := warningMetadataRequiredKeys(t)

	for _, path := range paths {
		t.Run(filepath.Base(path), func(t *testing.T) {
			fixture := decodeFile(t, path)
			if !containsString(fixtureExpectedLanguages(fixture), "go") {
				t.Skip("fixture does not declare Go coverage")
			}
			if expectedError, ok := asObject(fixture["expected"])["error"]; ok {
				code := asString(asObject(expectedError)["code"])
				defer func() {
					recovered := recover()
					if recovered == nil {
						t.Fatalf("expected panic containing %q", code)
					}
					if !strings.Contains(fmt.Sprint(recovered), code) {
						t.Fatalf("expected panic containing %q, got %v", code, recovered)
					}
				}()
				_ = runFixture(t, fixture)
				return
			}
			result := runFixture(t, fixture)
			validateCostLedger(t, result, filepath.Base(path)+":go", warningMetadataKeys)
			expected := asObject(asObject(fixture["expected"])["cost_ledger"])
			assertSubset(t, result, expected, filepath.Base(path))
		})
	}
}

func TestDefaultPriceCatalog(t *testing.T) {
	cache := DefaultSourceCache()
	metadata := asObject(cache["metadata"])
	if metadata["price_card_count"] == nil {
		t.Fatal("default source cache missing price_card_count")
	}
	cards := DefaultPriceCards()
	if len(cards) < 7000 {
		t.Fatalf("default price catalog is unexpectedly small: %d", len(cards))
	}
	if fmt.Sprint(len(cards)) != fmt.Sprint(metadata["price_card_count"]) {
		t.Fatalf("default catalog count mismatch: cards=%d metadata=%v", len(cards), metadata["price_card_count"])
	}
	if len(DefaultPriceSourcePriority) == 0 || DefaultPriceSourcePriority[0] != "llm-prices" {
		t.Fatalf("unexpected default source priority: %#v", DefaultPriceSourcePriority)
	}
}
