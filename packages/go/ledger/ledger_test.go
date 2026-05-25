package ledger

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"reflect"
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
	case "portkey":
		return PriceCardsFromPortkey(asObject(source["data"]))
	default:
		t.Fatalf("unsupported price source: %s", asString(source["type"]))
	}
	return nil
}

func runFixture(t *testing.T, fixture Object) Object {
	t.Helper()
	input := asObject(fixture["input"])
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
		case "from_llamaindex_token_counter":
			return FromLlamaIndexTokenCounter(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		default:
			return FromResponse(asObject(rawResponse), extractOptions, priceCards, discountPolicies)
		}
	}
	return CalculateCostWithOptions(asObject(input["usage_ledger"]), priceCards, discountPolicies, options)
}

func TestFixtures(t *testing.T) {
	paths, err := filepath.Glob("../../../fixtures/*.json")
	if err != nil {
		t.Fatal(err)
	}
	if len(paths) == 0 {
		t.Fatal("no fixtures found")
	}

	for _, path := range paths {
		t.Run(filepath.Base(path), func(t *testing.T) {
			fixture := decodeFile(t, path)
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
			expected := asObject(asObject(fixture["expected"])["cost_ledger"])
			assertSubset(t, result, expected, filepath.Base(path))
		})
	}
}
