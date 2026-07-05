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

func TestCalculateCostTypedSupportsBillingSchedules(t *testing.T) {
	usage := UsageLedger{
		SchemaVersion: "0.1",
		Provider:      "deepseek",
		Surface:       "deepseek.chat_completions",
		Model: ModelIdentity{
			Requested:       "deepseek-v4-pro",
			Billed:          "deepseek-v4-pro",
			AliasResolution: "none",
		},
		Context: Object{"priced_at": "2026-07-15T06:30:00Z"},
		Components: []UsageComponent{
			{Name: "output_text_tokens", Quantity: "1000000", Unit: "token"},
		},
	}

	schedule := BillingSchedule{
		Timezone:       "UTC",
		DefaultPeriod:  "regular",
		BoundaryPolicy: "start_inclusive_end_exclusive",
		Windows: []BillingWindow{
			{Period: "peak", Start: "01:00", End: "04:00"},
			{Period: "peak", Start: "06:00", End: "10:00"},
		},
	}
	priceCards := []PriceCard{
		{
			SchemaVersion:   "0.1",
			ID:              "deepseek:typed:regular",
			Provider:        "deepseek",
			Surface:         "deepseek.chat_completions",
			Model:           "deepseek-v4-pro",
			PricingPeriod:   "regular",
			BillingSchedule: &schedule,
			Components: []PriceComponent{
				{
					UsageComponent: "output_text_tokens",
					Unit:           "token",
					Price:          Price{Amount: "0.87", Currency: "USD", Per: "1000000"},
				},
			},
			Source: Source{Name: "typed-period-test"},
		},
		{
			SchemaVersion:   "0.1",
			ID:              "deepseek:typed:peak",
			Provider:        "deepseek",
			Surface:         "deepseek.chat_completions",
			Model:           "deepseek-v4-pro",
			PricingPeriod:   "peak",
			BillingSchedule: &schedule,
			Components: []PriceComponent{
				{
					UsageComponent: "output_text_tokens",
					Unit:           "token",
					Price:          Price{Amount: "1.74", Currency: "USD", Per: "1000000"},
				},
			},
			Source: Source{Name: "typed-period-test"},
		},
	}

	result := CalculateCostTyped(usage, priceCards, nil)
	if result["total"] != "1.74" {
		t.Fatalf("expected peak total 1.74, got %v", result["total"])
	}
	components := asSlice(result["components"])
	if len(components) != 1 {
		t.Fatalf("expected 1 cost component, got %d", len(components))
	}
	component := asObject(components[0])
	if asString(component["price_card_id"]) != "deepseek:typed:peak" {
		t.Fatalf("expected typed peak card to be selected, got %v", component)
	}
	metadata := asObject(component["metadata"])
	if asString(metadata["pricing_period"]) != "peak" || asString(metadata["pricing_window"]) != "06:00-10:00" {
		t.Fatalf("expected period metadata from typed schedule, got %v", metadata)
	}
}

func TestCalculateCostGuardsMalformedBillingSchedule(t *testing.T) {
	usage := Object{
		"schema_version": "0.1",
		"provider":       "deepseek",
		"surface":        "deepseek.chat_completions",
		"model": Object{
			"requested":        "deepseek-v4-pro",
			"billed":           "deepseek-v4-pro",
			"alias_resolution": "none",
		},
		"context": Object{"priced_at": "2026-07-15T01:30:00Z"},
		"components": []any{
			Object{"name": "output_text_tokens", "quantity": "1000000", "unit": "token"},
		},
	}
	malformedSchedule := Object{
		"timezone":        "UTC",
		"default_period":  "regular",
		"boundary_policy": "start_inclusive_end_exclusive",
		"windows": []any{
			Object{"period": "peak", "start": "25:00", "end": "04:00"},
		},
	}
	priceCards := []any{
		Object{
			"schema_version":   "0.1",
			"id":               "deepseek:malformed:regular",
			"provider":         "deepseek",
			"surface":          "deepseek.chat_completions",
			"model":            "deepseek-v4-pro",
			"pricing_period":   "regular",
			"billing_schedule": malformedSchedule,
			"components": []any{
				Object{
					"usage_component": "output_text_tokens",
					"unit":            "token",
					"price":           Object{"amount": "0.87", "currency": "USD", "per": "1000000"},
				},
			},
			"source": Object{"name": "runtime-guard"},
		},
		Object{
			"schema_version":   "0.1",
			"id":               "deepseek:malformed:peak",
			"provider":         "deepseek",
			"surface":          "deepseek.chat_completions",
			"model":            "deepseek-v4-pro",
			"pricing_period":   "peak",
			"billing_schedule": malformedSchedule,
			"components": []any{
				Object{
					"usage_component": "output_text_tokens",
					"unit":            "token",
					"price":           Object{"amount": "1.74", "currency": "USD", "per": "1000000"},
				},
			},
			"source": Object{"name": "runtime-guard"},
		},
	}

	result := CalculateCost(usage, priceCards, nil)
	if components := asSlice(result["components"]); len(components) != 0 {
		t.Fatalf("expected malformed schedule to remain unpriced, got %v", components)
	}
	warnings := asSlice(result["warnings"])
	if len(warnings) != 1 || asString(asObject(warnings[0])["code"]) != "billing_schedule_unsupported" {
		t.Fatalf("expected billing_schedule_unsupported warning, got %v", warnings)
	}
}
