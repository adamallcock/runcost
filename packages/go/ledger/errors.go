package ledger

import (
	"fmt"
	"runtime"
)

func recoverLedgerError(result *Object, err *error) {
	if failure := recover(); failure != nil {
		if _, programmingError := failure.(runtime.Error); programmingError {
			panic(failure)
		}
		*result = nil
		if cause, ok := failure.(error); ok {
			*err = fmt.Errorf("cost calculation failed: %w", cause)
		} else {
			*err = fmt.Errorf("cost calculation failed: %v", failure)
		}
	}
}

// CalculateCostWithOptionsE returns validation/strict failures as errors.
// Existing CalculateCostWithOptions retains its documented panic behavior.
func CalculateCostWithOptionsE(usage Object, cards []any, discounts []any, options Object) (result Object, err error) {
	defer recoverLedgerError(&result, &err)
	return CalculateCostWithOptions(usage, cards, discounts, options), nil
}

// CalculateCostTypedWithOptionsE is the typed error-returning calculation API.
func CalculateCostTypedWithOptionsE(usage UsageLedger, cards []PriceCard, discounts []DiscountPolicy, options CostOptions) (result Object, err error) {
	defer recoverLedgerError(&result, &err)
	return CalculateCostTypedWithOptions(usage, cards, discounts, options), nil
}

// FromResponseE returns validation and strict-mode failures as ordinary errors.
func FromResponseE(response Object, options Object, cards []any, discounts []any) (result Object, err error) {
	defer recoverLedgerError(&result, &err)
	return FromResponse(response, options, cards, discounts), nil
}
