package ledger

import "testing"

func TestCalculateCostTypedUsesSchemaShapedStructs(t *testing.T) {
	usage := UsageLedger{
		SchemaVersion: "0.1",
		Provider:      "openai",
		Surface:       "openai.responses",
		Model: ModelIdentity{
			Requested:       "gpt-example",
			Billed:          "gpt-example",
			AliasResolution: "none",
		},
		Context: Object{"service_tier": "standard"},
		Components: []UsageComponent{
			{Name: "input_uncached_tokens", Quantity: "1000", Unit: "token"},
			{Name: "output_text_tokens", Quantity: "250", Unit: "token"},
		},
	}

	priceCards := []PriceCard{
		{
			SchemaVersion: "0.1",
			ID:            "openai:gpt-example:standard",
			Provider:      "openai",
			Surface:       "openai.responses",
			Model:         "gpt-example",
			ServiceTier:   "standard",
			Components: []PriceComponent{
				{
					UsageComponent: "input_uncached_tokens",
					Unit:           "token",
					Price:          Price{Amount: "1", Currency: "USD", Per: "1000000"},
				},
				{
					UsageComponent: "output_text_tokens",
					Unit:           "token",
					Price:          Price{Amount: "2", Currency: "USD", Per: "1000000"},
				},
			},
			Source: Source{Name: "typed-test"},
		},
	}

	discounts := []DiscountPolicy{
		{
			SchemaVersion: "0.1",
			ID:            "openai-contract",
			Match:         DiscountMatch{Provider: "openai"},
			Adjustment:    DiscountAdjustment{Type: "percentage_discount", Value: "10"},
		},
	}

	result := CalculateCostTyped(usage, priceCards, discounts)

	if result["total"] != "0.00135" {
		t.Fatalf("expected discounted total 0.00135, got %v", result["total"])
	}
	components := asSlice(result["components"])
	if len(components) != 2 {
		t.Fatalf("expected 2 cost components, got %d", len(components))
	}
	if asString(asObject(components[0])["price_card_id"]) != "openai:gpt-example:standard" {
		t.Fatalf("expected typed price card id to be preserved, got %v", components[0])
	}
	priceSources := asSlice(result["price_sources"])
	if len(priceSources) != 1 || asString(asObject(priceSources[0])["name"]) != "typed-test" {
		t.Fatalf("expected typed price source to be preserved, got %v", priceSources)
	}
	appliedDiscounts := asSlice(result["applied_discounts"])
	if len(appliedDiscounts) != 2 {
		t.Fatalf("expected discount to apply to both components, got %d", len(appliedDiscounts))
	}
}
