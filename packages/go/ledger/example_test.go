package ledger

import "fmt"

func ExampleCalculateCost() {
	usageLedger := Object{
		"schema_version": "0.1",
		"provider":       "openai",
		"surface":        "openai.responses",
		"model": Object{
			"requested":        "gpt-example",
			"billed":           "gpt-example",
			"alias_resolution": "none",
		},
		"components": []any{
			Object{"name": "input_uncached_tokens", "quantity": "1000", "unit": "token"},
			Object{"name": "output_text_tokens", "quantity": "200", "unit": "token"},
		},
	}
	priceCards := []any{
		Object{
			"schema_version": "0.1",
			"id":             "openai:gpt-example:example",
			"provider":       "openai",
			"surface":        "openai.responses",
			"model":          "gpt-example",
			"components": []any{
				Object{"usage_component": "input_uncached_tokens", "unit": "token", "price": Object{"amount": "1", "currency": "USD", "per": "1000000"}},
				Object{"usage_component": "output_text_tokens", "unit": "token", "price": Object{"amount": "2", "currency": "USD", "per": "1000000"}},
			},
			"source": Object{"name": "example"},
		},
	}

	result := CalculateCost(usageLedger, priceCards, nil)
	fmt.Println(result["total"])
	// Output: 0.0014
}

func ExampleCalculateCostTyped() {
	usageLedger := UsageLedger{
		SchemaVersion: "0.1",
		Provider:      "openai",
		Surface:       "openai.responses",
		Model: ModelIdentity{
			Requested:       "gpt-example",
			Billed:          "gpt-example",
			AliasResolution: "none",
		},
		Components: []UsageComponent{
			{Name: "input_uncached_tokens", Quantity: "1000", Unit: "token"},
			{Name: "output_text_tokens", Quantity: "200", Unit: "token"},
		},
	}
	priceCards := []PriceCard{
		{
			SchemaVersion: "0.1",
			ID:            "openai:gpt-example:example",
			Provider:      "openai",
			Surface:       "openai.responses",
			Model:         "gpt-example",
			Components: []PriceComponent{
				{UsageComponent: "input_uncached_tokens", Unit: "token", Price: Price{Amount: "1", Currency: "USD", Per: "1000000"}},
				{UsageComponent: "output_text_tokens", Unit: "token", Price: Price{Amount: "2", Currency: "USD", Per: "1000000"}},
			},
			Source: Source{Name: "example"},
		},
	}

	result := CalculateCostTyped(usageLedger, priceCards, nil)
	fmt.Println(result["total"])
	// Output: 0.0014
}

func ExampleFromResponse() {
	response := Object{
		"model": "gpt-example",
		"usage": Object{
			"input_tokens":  100,
			"output_tokens": 50,
		},
	}
	priceCards := []any{
		Object{
			"schema_version": "0.1",
			"id":             "openai:gpt-example:example",
			"provider":       "openai",
			"surface":        "openai.responses",
			"model":          "gpt-example",
			"components": []any{
				Object{"usage_component": "input_uncached_tokens", "unit": "token", "price": Object{"amount": "1", "currency": "USD", "per": "1000000"}},
				Object{"usage_component": "output_text_tokens", "unit": "token", "price": Object{"amount": "2", "currency": "USD", "per": "1000000"}},
			},
			"source": Object{"name": "example"},
		},
	}

	result := FromResponse(response, Object{"surface": "openai.responses"}, priceCards, nil)
	fmt.Println(result["total"])
	// Output: 0.0002
}
