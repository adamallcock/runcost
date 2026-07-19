package ledger

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func expansionFixture(t *testing.T) Object {
	t.Helper()
	path := filepath.Join("..", "..", "..", "fixtures", "expansion", "cases.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var fixture Object
	if err := json.Unmarshal(data, &fixture); err != nil {
		t.Fatal(err)
	}
	return fixture
}

func expansionClone(value Object) Object {
	encoded, _ := json.Marshal(value)
	var result Object
	_ = json.Unmarshal(encoded, &result)
	return result
}

func expansionJSONValue(value any) any {
	encoded, _ := json.Marshal(value)
	var result any
	_ = json.Unmarshal(encoded, &result)
	return result
}

func assertExpansionSubset(t *testing.T, expected, actual any, path string) {
	t.Helper()
	switch expectedValue := expected.(type) {
	case map[string]any:
		actualValue, ok := actual.(map[string]any)
		if !ok {
			t.Fatalf("%s: expected object, got %T", path, actual)
		}
		for key, child := range expectedValue {
			actualChild, exists := actualValue[key]
			if !exists {
				t.Fatalf("%s.%s: missing", path, key)
			}
			assertExpansionSubset(t, child, actualChild, path+"."+key)
		}
	case []any:
		actualValue, ok := actual.([]any)
		if !ok || len(actualValue) != len(expectedValue) {
			t.Fatalf("%s: expected %d items, got %T/%d", path, len(expectedValue), actual, len(actualValue))
		}
		for index, child := range expectedValue {
			assertExpansionSubset(t, child, actualValue[index], fmt.Sprintf("%s[%d]", path, index))
		}
	default:
		if !reflect.DeepEqual(expected, actual) {
			t.Fatalf("%s: expected %#v, got %#v", path, expected, actual)
		}
	}
}

func expansionLanguages(testCase Object) []any {
	if languages := asSlice(testCase["expected_languages"]); languages != nil {
		return languages
	}
	return []any{"python", "javascript", "go"}
}

func includesExpansionLanguage(values []any, expected string) bool {
	for _, value := range values {
		if asString(value) == expected {
			return true
		}
	}
	return false
}

func runGoExpansionCase(t *testing.T, testCase, fixture Object) any {
	t.Helper()
	input := expansionClone(asObject(testCase["input"]))
	var priceCards []any
	if reference := asString(input["price_cards_ref"]); reference != "" {
		priceCards = asSlice(asObject(fixture["price_card_sets"])[reference])
		delete(input, "price_cards_ref")
	} else if rawCards := input["price_cards"]; rawCards != nil {
		priceCards = asSlice(rawCards)
		delete(input, "price_cards")
	}
	switch asString(testCase["operation"]) {
	case "from_response":
		response := asObject(input["response"])
		delete(input, "response")
		return FromResponse(response, input, priceCards, nil)
	case "from_batch_results":
		items := asSlice(input["items"])
		delete(input, "items")
		input["price_cards"] = priceCards
		return FromBatchResults(items, input)
	case "price_cards_from_genai_prices":
		data := input["data"]
		delete(input, "data")
		return PriceCardsFromGenAIPrices(data, input)
	case "usage_ledger_from_otel":
		span := asObject(input["span"])
		delete(input, "span")
		return UsageLedgerFromOTelGenAISpan(span, input)
	case "from_otel":
		span := asObject(input["span"])
		delete(input, "span")
		return FromOTelGenAISpan(span, input, priceCards, nil)
	case "estimate_cost":
		discountPolicies := asSlice(input["discount_policies"])
		delete(input, "discount_policies")
		return EstimateCost(input, priceCards, discountPolicies)
	case "attach_price_resolution":
		return AttachPriceResolution(asObject(input["ledger"]), asObject(input["resolution"]))
	case "evaluate_budget":
		total := input["ledger_or_total"]
		delete(input, "ledger_or_total")
		return EvaluateBudget(total, input)
	case "reconcile_cost":
		total := input["ledger_or_total"]
		reported := input["reported_total"]
		delete(input, "ledger_or_total")
		delete(input, "reported_total")
		return ReconcileCost(total, reported, input)
	default:
		t.Fatalf("unsupported expansion operation: %s", asString(testCase["operation"]))
		return nil
	}
}

func TestProductExpansionFixtures(t *testing.T) {
	fixture := expansionFixture(t)
	for _, rawCase := range asSlice(fixture["cases"]) {
		testCase := asObject(rawCase)
		if !includesExpansionLanguage(expansionLanguages(testCase), "go") {
			continue
		}
		t.Run(asString(testCase["id"]), func(t *testing.T) {
			actual := expansionJSONValue(runGoExpansionCase(t, testCase, fixture))
			expected := expansionJSONValue(testCase["expected"])
			assertExpansionSubset(t, expected, actual, "$"+asString(testCase["id"]))
		})
	}
}

func TestCompiledCatalogNarrowsCandidates(t *testing.T) {
	cards := []any{
		Object{"provider": "a", "model": "m", "aliases": []any{"alias"}},
		Object{"provider": "b", "model": "m"},
	}
	compiled := CompilePriceCatalog(cards)
	if len(compiled.identityCandidates(Object{"provider": "a", "model": Object{"billed": "alias"}})) != 1 {
		t.Fatal("compiled provider/alias index did not narrow to one card")
	}
	if len(compiled.modelCandidates(Object{"model": Object{"billed": "m"}})) != 2 {
		t.Fatal("compiled model index did not retain cross-provider candidates")
	}
}

func TestCatalogManifestRejectsMalformedInput(t *testing.T) {
	for _, manifest := range []Object{{}, {"algorithm": "md5", "catalog": Object{}}} {
		valid, _ := VerifyCatalogManifest(manifest, t.TempDir())["valid"].(bool)
		if valid {
			t.Fatal("malformed catalog manifest was accepted")
		}
	}
}

func expectExpansionPanic(t *testing.T, contains string, callback func()) {
	t.Helper()
	deferred := false
	func() {
		defer func() {
			if recovered := recover(); recovered != nil {
				deferred = true
				if !strings.Contains(fmt.Sprint(recovered), contains) {
					t.Fatalf("panic %q does not contain %q", recovered, contains)
				}
			}
		}()
		callback()
	}()
	if !deferred {
		t.Fatalf("expected panic containing %q", contains)
	}
}

func TestExpansionEdgeCases(t *testing.T) {
	empty := FromBatchResults(nil, Object{"provider": "openai"})
	expectedSummary := Object{"total": 0, "succeeded": 0, "failed": 0, "pending": 0, "total_cost": "0"}
	if !reflect.DeepEqual(empty["summary"], expectedSummary) || len(asSlice(empty["warnings"])) != 0 {
		t.Fatalf("empty batch summary is unstable: %#v", empty)
	}
	expectExpansionPanic(t, "unsupported batch provider", func() {
		FromBatchResults(nil, Object{"provider": "unsupported"})
	})
	if asString(EvaluateBudget("0", Object{"budget": "0"})["status"]) != "within_budget" {
		t.Fatal("an unspent zero budget must remain within budget")
	}
	expectExpansionPanic(t, "budget must be non-negative", func() {
		EvaluateBudget("0", Object{"budget": "-1"})
	})
	expectExpansionPanic(t, "warning_threshold must be between 0 and 1", func() {
		EvaluateBudget("0", Object{"budget": "1", "warning_threshold": "1.1"})
	})
	expectExpansionPanic(t, "tolerance must be non-negative", func() {
		ReconcileCost("1", "1", Object{"tolerance": "-0.01"})
	})
	unknown := FromResponse(Object{"unexpected": true}, Object{}, nil, nil)
	warnings := asSlice(unknown["warnings"])
	if len(warnings) != 1 || asString(asObject(warnings[0])["code"]) != "unknown_surface" {
		t.Fatalf("ambiguous response did not preserve unknown_surface: %#v", unknown)
	}
	duplicateCards := PriceCardsFromGenAIPrices(Object{
		"providers": []any{
			Object{
				"id": "duplicate-fixture",
				"models": []any{
					Object{
						"id": "model",
						"prices": []any{
							Object{"constraint": Object{"start_date": "2026-01-01"}, "prices": Object{"input_mtok": "1"}},
							Object{"constraint": Object{"start_date": "2026-01-01"}, "prices": Object{"input_mtok": "2"}},
						},
					},
				},
			},
		},
	})
	ids := map[string]bool{}
	for _, card := range duplicateCards {
		ids[asString(asObject(card)["id"])] = true
	}
	if len(duplicateCards) != 2 || len(ids) != 2 {
		t.Fatalf("genai-prices duplicate IDs were not disambiguated: %#v", duplicateCards)
	}
}
