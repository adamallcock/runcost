package ledger

import (
	"encoding/json"
	"fmt"
	"math/big"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Object is the prototype map-backed representation for canonical ledgers,
// price cards, discount policies, provider responses, and adapter inputs.
type Object = map[string]any

func numberString(value any) string {
	if value == nil {
		return "0"
	}
	switch typed := value.(type) {
	case string:
		return typed
	case json.Number:
		return typed.String()
	case float64:
		return strconv.FormatFloat(typed, 'f', -1, 64)
	case int:
		return strconv.Itoa(typed)
	case int64:
		return strconv.FormatInt(typed, 10)
	default:
		return fmt.Sprint(typed)
	}
}

func rat(value any) *big.Rat {
	parsed, ok := new(big.Rat).SetString(numberString(value))
	if !ok {
		panic(fmt.Sprintf("invalid decimal: %v", value))
	}
	return parsed
}

func decimal(value *big.Rat) string {
	text := value.FloatString(18)
	text = strings.TrimRight(text, "0")
	text = strings.TrimRight(text, ".")
	if text == "-0" || text == "" {
		return "0"
	}
	return text
}

func add(left any, right any) string {
	return decimal(new(big.Rat).Add(rat(left), rat(right)))
}

func subtract(left any, right any) string {
	return decimal(new(big.Rat).Sub(rat(left), rat(right)))
}

func multiplyDivide(quantity any, amount any, per any) string {
	perRat := rat(per)
	if perRat.Sign() == 0 {
		panic("price.per must not be zero")
	}
	result := new(big.Rat).Mul(rat(quantity), rat(amount))
	result.Quo(result, perRat)
	return decimal(result)
}

func asObject(value any) Object {
	if value == nil {
		return Object{}
	}
	return value.(map[string]any)
}

func asSlice(value any) []any {
	if value == nil {
		return nil
	}
	return value.([]any)
}

func asString(value any) string {
	if value == nil {
		return ""
	}
	return value.(string)
}

func billedModel(usageLedger Object) string {
	model := asObject(usageLedger["model"])
	for _, key := range []string{"billed", "returned", "requested"} {
		if value := asString(model[key]); value != "" {
			return value
		}
	}
	return ""
}

func datePart(value any) string {
	if value == nil {
		return ""
	}
	text := fmt.Sprint(value)
	if len(text) < 10 {
		return ""
	}
	return text[:10]
}

func dateValue(value any) (time.Time, bool) {
	part := datePart(value)
	if part == "" {
		return time.Time{}, false
	}
	parsed, err := time.Parse("2006-01-02", part)
	if err != nil {
		return time.Time{}, false
	}
	return parsed, true
}

func usageContext(usageLedger Object) Object {
	return asObject(usageLedger["context"])
}

func containsString(values []any, target string) bool {
	for _, value := range values {
		if asString(value) == target {
			return true
		}
	}
	return false
}

func cardIdentityMatches(usageLedger Object, card Object) bool {
	model := billedModel(usageLedger)
	modelMatches := asString(card["model"]) == model || containsString(asSlice(card["aliases"]), model)
	providerMatches := asString(card["provider"]) == asString(usageLedger["provider"])
	surface := asString(card["surface"])
	surfaceMatches := surface == "" || surface == asString(usageLedger["surface"])
	return modelMatches && providerMatches && surfaceMatches
}

func effectiveMatches(card Object, pricedAt string) bool {
	if pricedAt == "" {
		return true
	}
	effective := asObject(card["effective"])
	fromDate := asString(effective["from"])
	toDate := asString(effective["to"])
	if fromDate != "" && pricedAt < fromDate {
		return false
	}
	if toDate != "" && pricedAt > toDate {
		return false
	}
	return true
}

func cardContextMatches(usageLedger Object, card Object) bool {
	context := usageContext(usageLedger)
	serviceTier := asString(context["service_tier"])
	region := asString(context["region"])
	if serviceTier != "" && asString(card["service_tier"]) != "" && asString(card["service_tier"]) != serviceTier {
		return false
	}
	if region != "" && asString(card["region"]) != "" && asString(card["region"]) != region {
		return false
	}
	return effectiveMatches(card, datePart(context["priced_at"]))
}

func cardScore(usageLedger Object, card Object) int {
	context := usageContext(usageLedger)
	score := 0
	if asString(card["surface"]) == asString(usageLedger["surface"]) {
		score += 8
	}
	if asString(context["service_tier"]) != "" && asString(card["service_tier"]) == asString(context["service_tier"]) {
		score += 4
	}
	if asString(context["region"]) != "" && asString(card["region"]) == asString(context["region"]) {
		score += 2
	}
	if card["effective"] != nil {
		score++
	}
	return score
}

func sourcePriorityScore(card Object, options Object) int {
	priority := asSlice(options["price_source_priority"])
	if len(priority) == 0 {
		priority = asSlice(options["priceSourcePriority"])
	}
	if len(priority) == 0 {
		return 0
	}
	sourceName := asString(asObject(card["source"])["name"])
	for index, value := range priority {
		if asString(value) == sourceName {
			return (len(priority) - index) * 100
		}
	}
	return 0
}

func hasSourcePriority(options Object) bool {
	return len(asSlice(options["price_source_priority"])) > 0 || len(asSlice(options["priceSourcePriority"])) > 0
}

func sourcePriority(options Object) []any {
	priority := asSlice(options["price_source_priority"])
	if len(priority) == 0 {
		priority = asSlice(options["priceSourcePriority"])
	}
	return priority
}

func matchingCards(usageLedger Object, priceCards []any, options Object) []Object {
	type scoredCard struct {
		card  Object
		index int
		score int
	}
	scored := []scoredCard{}
	for _, rawCard := range priceCards {
		card := asObject(rawCard)
		if !cardIdentityMatches(usageLedger, card) || !cardContextMatches(usageLedger, card) {
			continue
		}
		score := cardScore(usageLedger, card) + sourcePriorityScore(card, options)
		scored = append(scored, scoredCard{card: card, index: len(scored), score: score})
	}
	sort.SliceStable(scored, func(left int, right int) bool {
		if scored[left].score != scored[right].score {
			return scored[left].score > scored[right].score
		}
		return scored[left].index < scored[right].index
	})
	cards := []Object{}
	for _, item := range scored {
		cards = append(cards, item.card)
	}
	return cards
}

func totalInputTokens(usageLedger Object) *big.Rat {
	context := usageContext(usageLedger)
	if context["total_input_tokens"] != nil {
		return rat(context["total_input_tokens"])
	}
	total := big.NewRat(0, 1)
	for _, rawComponent := range asSlice(usageLedger["components"]) {
		component := asObject(rawComponent)
		if asString(component["unit"]) == "token" && strings.HasPrefix(asString(component["name"]), "input_") {
			total.Add(total, rat(component["quantity"]))
		}
	}
	return total
}

func conditionsMatch(usageLedger Object, priceComponent Object) bool {
	conditions := asObject(priceComponent["conditions"])
	if len(conditions) == 0 {
		return true
	}
	totalInput := totalInputTokens(usageLedger)
	if conditions["min_total_input_tokens"] != nil && totalInput.Cmp(rat(conditions["min_total_input_tokens"])) < 0 {
		return false
	}
	if conditions["max_total_input_tokens"] != nil && totalInput.Cmp(rat(conditions["max_total_input_tokens"])) > 0 {
		return false
	}
	return true
}

func candidatePriceComponents(priceCards []Object, component Object) []Object {
	matches := []Object{}
	for _, card := range priceCards {
		for _, rawPriceComponent := range asSlice(card["components"]) {
			priceComponent := asObject(rawPriceComponent)
			if asString(priceComponent["usage_component"]) == asString(component["name"]) &&
				asString(priceComponent["unit"]) == asString(component["unit"]) {
				matches = append(matches, Object{"card": card, "price_component": priceComponent})
			}
		}
	}
	return matches
}

func findPriceComponents(usageLedger Object, priceCards []Object, component Object) []Object {
	matches := []Object{}
	for _, match := range candidatePriceComponents(priceCards, component) {
		if conditionsMatch(usageLedger, asObject(match["price_component"])) {
			matches = append(matches, match)
		}
	}
	return matches
}

func longContextRuleMissingWarning(usageLedger Object, candidates []Object, component Object) (Object, bool) {
	if len(candidates) == 0 {
		return nil, false
	}
	hasConditions := false
	for _, match := range candidates {
		if len(asObject(asObject(match["price_component"])["conditions"])) > 0 {
			hasConditions = true
			break
		}
	}
	if !hasConditions {
		return nil, false
	}
	return Object{
		"code":    "long_context_rule_missing",
		"message": fmt.Sprintf("No long-context pricing rule matched %s at %s input tokens.", asString(component["name"]), decimal(totalInputTokens(usageLedger))),
	}, true
}

func hasPriceCardForUsage(usageLedger Object, priceCards []any) bool {
	for _, rawCard := range priceCards {
		card := asObject(rawCard)
		if cardIdentityMatches(usageLedger, card) {
			return true
		}
	}
	return false
}

func noMatchingCardWarning(usageLedger Object, priceCards []any) Object {
	context := usageContext(usageLedger)
	identityCards := []Object{}
	for _, rawCard := range priceCards {
		card := asObject(rawCard)
		if cardIdentityMatches(usageLedger, card) {
			identityCards = append(identityCards, card)
		}
	}
	serviceTier := asString(context["service_tier"])
	if serviceTier != "" && len(identityCards) > 0 {
		allMismatch := true
		for _, card := range identityCards {
			if asString(card["service_tier"]) == "" || asString(card["service_tier"]) == serviceTier {
				allMismatch = false
				break
			}
		}
		if allMismatch {
			return Object{
				"code":    "service_tier_unsupported",
				"message": fmt.Sprintf("No price card found for service tier %s.", serviceTier),
			}
		}
	}
	pricedAt := datePart(context["priced_at"])
	if pricedAt != "" && len(identityCards) > 0 {
		anyEffective := false
		for _, card := range identityCards {
			if effectiveMatches(card, pricedAt) {
				anyEffective = true
				break
			}
		}
		if !anyEffective {
			return Object{
				"code":    "historical_price_missing",
				"message": fmt.Sprintf("No price card effective for %s.", pricedAt),
			}
		}
	}
	return Object{
		"code":    "price_not_found",
		"message": fmt.Sprintf("No price card matched provider, surface, model, and context for %s.", billedModel(usageLedger)),
	}
}

func policyMatches(policy Object, usageLedger Object, component Object) bool {
	match := asObject(policy["match"])
	model := billedModel(usageLedger)
	if value := asString(match["provider"]); value != "" && value != asString(usageLedger["provider"]) {
		return false
	}
	if value := asString(match["surface"]); value != "" && value != asString(usageLedger["surface"]) {
		return false
	}
	if value := asString(match["model"]); value != "" && value != model {
		return false
	}
	context := usageContext(usageLedger)
	if value := asString(match["service_tier"]); value != "" && value != asString(context["service_tier"]) {
		return false
	}
	if value := asString(match["region"]); value != "" && value != asString(context["region"]) {
		return false
	}
	if components := asSlice(match["components"]); len(components) > 0 && !containsString(components, asString(component["name"])) {
		return false
	}
	if excluded := asSlice(match["exclude_components"]); len(excluded) > 0 && containsString(excluded, asString(component["name"])) {
		return false
	}
	return true
}

func discountEligible(priceComponent Object) bool {
	value, ok := priceComponent["discount_eligible"]
	if !ok {
		return true
	}
	return value.(bool)
}

func applyDiscounts(cost string, policies []any, usageLedger Object, component Object, eligible bool) (string, []any) {
	if !eligible {
		return cost, nil
	}

	current := cost
	applied := []any{}
	for _, rawPolicy := range policies {
		policy := asObject(rawPolicy)
		if !policyMatches(policy, usageLedger, component) {
			continue
		}

		before := current
		adjustment := asObject(policy["adjustment"])
		switch asString(adjustment["type"]) {
		case "multiplier":
			current = multiplyDivide(current, adjustment["value"], "1")
		case "percentage_discount":
			multiplier := subtract("1", multiplyDivide(adjustment["value"], "1", "100"))
			current = multiplyDivide(current, multiplier, "1")
		case "percentage_markup":
			multiplier := add("1", multiplyDivide(adjustment["value"], "1", "100"))
			current = multiplyDivide(current, multiplier, "1")
		}
		applied = append(applied, Object{
			"policy_id": asString(policy["id"]),
			"component": asString(component["name"]),
			"amount":    subtract(before, current),
		})
	}
	return current, applied
}

func optionalInt(value any) (int, bool) {
	if value == nil {
		return 0, false
	}
	switch typed := value.(type) {
	case int:
		return typed, true
	case int64:
		return int(typed), true
	case float64:
		return int(typed), true
	case json.Number:
		parsed, err := typed.Int64()
		if err == nil {
			return int(parsed), true
		}
	case string:
		parsed, err := strconv.Atoi(typed)
		if err == nil {
			return parsed, true
		}
	}
	return 0, false
}

func staleAfterDays(usageLedger Object, options Object) (int, bool) {
	if value, ok := optionalInt(options["stale_after_days"]); ok {
		return value, true
	}
	if value, ok := optionalInt(options["staleAfterDays"]); ok {
		return value, true
	}
	context := usageContext(usageLedger)
	if value, ok := optionalInt(context["stale_after_days"]); ok {
		return value, true
	}
	return optionalInt(context["price_stale_after_days"])
}

func stalePriceWarning(usageLedger Object, card Object, options Object) (Object, bool) {
	threshold, ok := staleAfterDays(usageLedger, options)
	if !ok {
		return nil, false
	}
	pricedAt, ok := dateValue(usageContext(usageLedger)["priced_at"])
	if !ok {
		return nil, false
	}
	retrievedAt, ok := dateValue(asObject(card["source"])["retrieved_at"])
	if !ok {
		return nil, false
	}
	ageDays := int(pricedAt.Sub(retrievedAt).Hours() / 24)
	if ageDays <= threshold {
		return nil, false
	}
	sourceName := asString(asObject(card["source"])["name"])
	if sourceName == "" {
		sourceName = "unknown"
	}
	return Object{
		"code":    "price_stale",
		"message": fmt.Sprintf("Price source %s is %d days old; threshold is %d days.", sourceName, ageDays, threshold),
	}, true
}

func providerReportedWarning(total string, options Object) (Object, bool) {
	mode := asString(options["provider_reported_cost_mode"])
	if mode == "" {
		mode = asString(options["providerReportedCostMode"])
	}
	if mode == "" {
		mode = "compare"
	}
	if mode != "compare" {
		return nil, false
	}
	reported := options["provider_reported_cost"]
	if reported == nil {
		reported = options["providerReportedCost"]
	}
	if reported == nil {
		return nil, false
	}
	providerTotal := decimal(rat(reported))
	if providerTotal == total {
		return nil, false
	}
	return Object{
		"code":    "provider_reported_cost_mismatch",
		"message": fmt.Sprintf("Provider reported cost %s differs from calculated total %s.", providerTotal, total),
	}, true
}

func applyProviderReportedCostUse(total string, components []any, warnings []any, options Object) (string, []any, []any) {
	mode := asString(options["provider_reported_cost_mode"])
	if mode == "" {
		mode = asString(options["providerReportedCostMode"])
	}
	if mode != "use" {
		return total, components, warnings
	}
	reported := options["provider_reported_cost"]
	if reported == nil {
		reported = options["providerReportedCost"]
	}
	if reported == nil {
		return total, components, warnings
	}
	providerTotal := decimal(rat(reported))
	adjustment := subtract(providerTotal, total)
	if adjustment != "0" {
		components = append(components, Object{
			"name":              "custom_units",
			"quantity":          adjustment,
			"unit":              "usd",
			"unit_price":        "1",
			"cost":              adjustment,
			"price_card_id":     "__provider_reported_cost__",
			"discount_eligible": false,
			"metadata": Object{
				"reason":                 "provider_reported_cost_reconciliation",
				"calculated_total":       total,
				"provider_reported_cost": providerTotal,
			},
		})
	}
	warnings = append(warnings, Object{
		"code":    "provider_reported_cost_used",
		"message": fmt.Sprintf("Provider reported cost %s used as authoritative total.", providerTotal),
	})
	return providerTotal, components, warnings
}

func priceSourceDisagreementWarning(matches []Object, component Object, options Object) (Object, bool) {
	if hasSourcePriority(options) || len(matches) < 2 {
		return nil, false
	}
	unitPrices := map[string]bool{}
	for _, match := range matches {
		price := asObject(asObject(match["price_component"])["price"])
		unitPrices[multiplyDivide(price["amount"], "1", price["per"])] = true
	}
	if len(unitPrices) <= 1 {
		return nil, false
	}
	chosen := asString(asObject(matches[0]["card"])["id"])
	return Object{
		"code":    "price_source_disagreement",
		"message": fmt.Sprintf("Multiple price sources disagree for %s; using %s.", asString(component["name"]), chosen),
	}, true
}

func debugTraceEnabled(options Object) bool {
	if value, ok := options["debug_trace"].(bool); ok && value {
		return true
	}
	if value, ok := options["debugTrace"].(bool); ok && value {
		return true
	}
	return false
}

func newDebugTrace() Object {
	return Object{
		"schema_version": "0.1",
		"decisions":      []any{},
		"summary": Object{
			"priced_components":   0,
			"unpriced_components": 0,
			"warnings":            0,
			"applied_discounts":   0,
		},
	}
}

func appendTraceDecision(trace Object, decision Object) {
	if trace == nil {
		return
	}
	trace["decisions"] = append(asSlice(trace["decisions"]), decision)
}

func incrementTraceSummary(trace Object, key string) {
	if trace == nil {
		return
	}
	summary := asObject(trace["summary"])
	current := 0
	if value, ok := optionalInt(summary[key]); ok {
		current = value
	}
	summary[key] = current + 1
}

func setTraceSummary(trace Object, key string, value int) {
	if trace == nil {
		return
	}
	asObject(trace["summary"])[key] = value
}

func priceCardIDs(cards []Object) []any {
	ids := []any{}
	for _, card := range cards {
		ids = append(ids, asString(card["id"]))
	}
	return ids
}

func matchPriceCardIDs(matches []Object) []any {
	ids := []any{}
	for _, match := range matches {
		ids = append(ids, asString(asObject(match["card"])["id"]))
	}
	return ids
}

// CalculateCost returns a componentized cost ledger for normalized usage,
// canonical price cards, and optional discount policies.
//
// It runs in compatibility mode, which means unknown or unpriced inputs produce
// warnings instead of panics.
func CalculateCost(usageLedger Object, priceCards []any, discountPolicies []any) Object {
	return CalculateCostWithMode(usageLedger, priceCards, discountPolicies, "compatibility")
}

// CalculateCostWithMode returns a componentized cost ledger using either
// "compatibility" or "strict" mode. Strict mode panics when warnings would be
// emitted, which is useful for tests and fail-closed billing workflows.
func CalculateCostWithMode(usageLedger Object, priceCards []any, discountPolicies []any, mode string) Object {
	return CalculateCostWithOptions(usageLedger, priceCards, discountPolicies, Object{"mode": mode})
}

// CalculateCostWithOptions returns a componentized cost ledger using
// compatibility options such as strict mode, stale price thresholds, and
// provider-reported cost comparison.
func CalculateCostWithOptions(usageLedger Object, priceCards []any, discountPolicies []any, options Object) Object {
	components := []any{}
	warnings := []any{}
	appliedDiscounts := []any{}
	sourceByName := map[string]Object{}
	sourceNames := []string{}
	var trace Object
	if debugTraceEnabled(options) {
		trace = newDebugTrace()
	}
	total := "0"
	resolvedBilledModel := billedModel(usageLedger)
	aliasResolution := asString(asObject(usageLedger["model"])["alias_resolution"])
	if aliasResolution == "" {
		aliasResolution = "none"
	}
	mode := asString(options["mode"])
	if mode == "" {
		mode = "compatibility"
	}
	hasModelCard := hasPriceCardForUsage(usageLedger, priceCards)
	candidateCards := matchingCards(usageLedger, priceCards, options)
	if trace != nil {
		appendTraceDecision(trace, Object{
			"type":                     "price_card_candidates",
			"model":                    resolvedBilledModel,
			"candidate_price_card_ids": priceCardIDs(candidateCards),
			"source_priority":          sourcePriority(options),
		})
	}
	warnedUnknownModel := false
	warnedNoMatchingCard := false
	warnedStaleCards := map[string]bool{}

	for _, rawComponent := range asSlice(usageLedger["components"]) {
		component := asObject(rawComponent)
		if !hasModelCard {
			if !warnedUnknownModel {
				warnings = append(warnings, Object{
					"code":    "unknown_model",
					"message": fmt.Sprintf("No price card found for %s.", resolvedBilledModel),
				})
				warnedUnknownModel = true
			}
			incrementTraceSummary(trace, "unpriced_components")
			continue
		}

		if len(candidateCards) == 0 {
			if !warnedNoMatchingCard {
				warnings = append(warnings, noMatchingCardWarning(usageLedger, priceCards))
				warnedNoMatchingCard = true
			}
			incrementTraceSummary(trace, "unpriced_components")
			continue
		}

		candidates := candidatePriceComponents(candidateCards, component)
		matches := []Object{}
		for _, match := range candidates {
			if conditionsMatch(usageLedger, asObject(match["price_component"])) {
				matches = append(matches, match)
			}
		}
		if len(matches) == 0 {
			if warning, ok := longContextRuleMissingWarning(usageLedger, candidates, component); ok {
				warnings = append(warnings, warning)
			} else {
				code := "component_unpriced"
				if strings.Contains(asString(component["name"]), "tool") {
					code = "tool_component_unpriced"
				}
				warnings = append(warnings, Object{
					"code":    code,
					"message": fmt.Sprintf("No price found for %s (%s).", asString(component["name"]), asString(component["unit"])),
				})
			}
			incrementTraceSummary(trace, "unpriced_components")
			continue
		}

		if warning, ok := priceSourceDisagreementWarning(matches, component, options); ok {
			warnings = append(warnings, warning)
		}
		card := asObject(matches[0]["card"])
		priceComponent := asObject(matches[0]["price_component"])
		appendTraceDecision(trace, Object{
			"type":                     "price_component_match",
			"component":                asString(component["name"]),
			"candidate_price_card_ids": matchPriceCardIDs(matches),
			"selected_price_card_id":   asString(card["id"]),
			"selected_source":          asString(asObject(card["source"])["name"]),
		})
		if asString(card["model"]) != resolvedBilledModel && containsString(asSlice(card["aliases"]), resolvedBilledModel) {
			previousBilledModel := resolvedBilledModel
			resolvedBilledModel = asString(card["model"])
			if aliasResolution == "none" {
				aliasResolution = "source_exact"
			}
			appendTraceDecision(trace, Object{
				"type":          "model_alias_resolution",
				"from":          previousBilledModel,
				"to":            resolvedBilledModel,
				"price_card_id": asString(card["id"]),
				"resolution":    aliasResolution,
			})
		}

		price := asObject(priceComponent["price"])
		baseCost := multiplyDivide(component["quantity"], price["amount"], price["per"])
		eligible := discountEligible(priceComponent)
		finalCost, applied := applyDiscounts(baseCost, discountPolicies, usageLedger, component, eligible)
		appliedDiscounts = append(appliedDiscounts, applied...)
		for _, rawApplied := range applied {
			appliedItem := asObject(rawApplied)
			appendTraceDecision(trace, Object{
				"type":      "discount_application",
				"component": asString(appliedItem["component"]),
				"policy_id": asString(appliedItem["policy_id"]),
				"amount":    asString(appliedItem["amount"]),
			})
		}
		total = add(total, finalCost)

		source := asObject(card["source"])
		sourceName := asString(source["name"])
		if _, exists := sourceByName[sourceName]; !exists {
			sourceNames = append(sourceNames, sourceName)
		}
		sourceByName[sourceName] = source
		cardID := asString(card["id"])
		if !warnedStaleCards[cardID] {
			if warning, ok := stalePriceWarning(usageLedger, card, options); ok {
				warnings = append(warnings, warning)
				warnedStaleCards[cardID] = true
			}
		}

		components = append(components, Object{
			"name":              asString(component["name"]),
			"quantity":          numberString(component["quantity"]),
			"unit":              asString(component["unit"]),
			"unit_price":        multiplyDivide(price["amount"], "1", price["per"]),
			"cost":              finalCost,
			"price_card_id":     asString(card["id"]),
			"discount_eligible": eligible,
		})
		incrementTraceSummary(trace, "priced_components")
	}

	priceSources := []any{}
	for _, name := range sourceNames {
		priceSources = append(priceSources, sourceByName[name])
	}
	total, components, warnings = applyProviderReportedCostUse(total, components, warnings, options)
	if warning, ok := providerReportedWarning(total, options); ok {
		warnings = append(warnings, warning)
	}
	if trace != nil {
		for _, rawWarning := range warnings {
			warning := asObject(rawWarning)
			appendTraceDecision(trace, Object{
				"type":         "warning",
				"warning_code": asString(warning["code"]),
				"message":      asString(warning["message"]),
			})
		}
		setTraceSummary(trace, "warnings", len(warnings))
		setTraceSummary(trace, "applied_discounts", len(appliedDiscounts))
	}

	model := asObject(usageLedger["model"])
	result := Object{
		"schema_version": "0.1",
		"provider":       asString(usageLedger["provider"]),
		"surface":        asString(usageLedger["surface"]),
		"model": Object{
			"requested":        asString(model["requested"]),
			"returned":         asString(model["returned"]),
			"billed":           resolvedBilledModel,
			"alias_resolution": aliasResolution,
		},
		"currency":          "USD",
		"components":        components,
		"total":             total,
		"price_sources":     priceSources,
		"applied_discounts": appliedDiscounts,
		"warnings":          warnings,
	}
	if trace != nil {
		result["debug_trace"] = trace
	}
	if mode == "strict" && len(warnings) > 0 {
		panic(fmt.Sprintf("strict mode cost calculation failed: %s", asString(asObject(warnings[0])["code"])))
	}
	return result
}

func sourceKey(source Object) string {
	return strings.Join([]string{
		asString(source["name"]),
		asString(source["url"]),
		asString(source["retrieved_at"]),
		asString(source["version"]),
	}, "|")
}

func componentKey(component Object) string {
	discountEligible := "true"
	if value, ok := component["discount_eligible"].(bool); ok {
		discountEligible = strconv.FormatBool(value)
	}
	return strings.Join([]string{
		asString(component["name"]),
		asString(component["unit"]),
		asString(component["unit_price"]),
		asString(component["price_card_id"]),
		discountEligible,
	}, "|")
}

func optionalBool(value any) (bool, bool) {
	if value == nil {
		return false, false
	}
	typed, ok := value.(bool)
	return typed, ok
}

func streamUsageMissingWarning(expectedLedgerCount any, actualLedgerCount int) Object {
	metadata := Object{"actual_ledger_count": actualLedgerCount}
	if expectedLedgerCount != nil {
		metadata["expected_ledger_count"] = expectedLedgerCount
	}
	return Object{
		"code":     "stream_usage_missing",
		"message":  "Final streaming usage was expected but not observed; aggregate total may be incomplete.",
		"metadata": metadata,
	}
}

// AggregateCostLedgers merges already-calculated cost ledgers into a single
// session or multi-call ledger.
func AggregateCostLedgers(costLedgers []any, options Object) Object {
	provider := asString(options["provider"])
	if provider == "" {
		provider = "aggregate"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "aggregate.cost_ledgers"
	}
	model := asString(options["model"])
	if model == "" {
		model = "multiple"
	}
	mode := asString(options["mode"])
	if mode == "" {
		mode = "compatibility"
	}

	componentsByKey := map[string]Object{}
	componentKeys := []string{}
	sourcesByKey := map[string]Object{}
	sourceKeys := []string{}
	appliedDiscounts := []any{}
	warnings := []any{}
	total := "0"

	for ledgerIndex, rawLedger := range costLedgers {
		ledger := asObject(rawLedger)
		total = add(total, ledger["total"])
		for _, rawComponent := range asSlice(ledger["components"]) {
			component := asObject(rawComponent)
			key := componentKey(component)
			if _, ok := componentsByKey[key]; !ok {
				merged := Object{
					"name":       asString(component["name"]),
					"quantity":   "0",
					"unit":       asString(component["unit"]),
					"unit_price": asString(component["unit_price"]),
					"cost":       "0",
					"metadata":   Object{"source_ledger_indexes": []any{}},
				}
				if component["price_card_id"] != nil {
					merged["price_card_id"] = component["price_card_id"]
				}
				if component["discount_eligible"] != nil {
					merged["discount_eligible"] = component["discount_eligible"]
				}
				componentsByKey[key] = merged
				componentKeys = append(componentKeys, key)
			}
			merged := componentsByKey[key]
			merged["quantity"] = add(merged["quantity"], component["quantity"])
			merged["cost"] = add(merged["cost"], component["cost"])
			metadata := asObject(merged["metadata"])
			metadata["source_ledger_indexes"] = append(asSlice(metadata["source_ledger_indexes"]), ledgerIndex)
		}
		for _, rawSource := range asSlice(ledger["price_sources"]) {
			source := asObject(rawSource)
			key := sourceKey(source)
			if _, ok := sourcesByKey[key]; !ok {
				sourcesByKey[key] = source
				sourceKeys = append(sourceKeys, key)
			}
		}
		appliedDiscounts = append(appliedDiscounts, asSlice(ledger["applied_discounts"])...)
		warnings = append(warnings, asSlice(ledger["warnings"])...)
	}

	expectedCount := options["expected_ledger_count"]
	if expectedCount == nil {
		expectedCount = options["expectedLedgerCount"]
	}
	finalExpected, _ := optionalBool(options["stream_final_usage_expected"])
	if value, ok := optionalBool(options["streamFinalUsageExpected"]); ok {
		finalExpected = value
	}
	finalPresent := true
	if value, ok := optionalBool(options["stream_final_usage_present"]); ok {
		finalPresent = value
	}
	if value, ok := optionalBool(options["streamFinalUsagePresent"]); ok {
		finalPresent = value
	}
	missingStreamUsageWarned := false
	if finalExpected && !finalPresent {
		warnings = append(warnings, streamUsageMissingWarning(expectedCount, len(costLedgers)))
		missingStreamUsageWarned = true
	}
	if !missingStreamUsageWarned && expectedCount != nil {
		if parsedExpectedCount, ok := optionalInt(expectedCount); ok && len(costLedgers) < parsedExpectedCount {
			warnings = append(warnings, streamUsageMissingWarning(expectedCount, len(costLedgers)))
		}
	}

	components := []any{}
	for _, key := range componentKeys {
		components = append(components, componentsByKey[key])
	}
	priceSources := []any{}
	for _, key := range sourceKeys {
		priceSources = append(priceSources, sourcesByKey[key])
	}
	metadata := Object{
		"ledger_count": len(costLedgers),
		"aggregation":  "cost_ledgers",
	}
	if expectedCount != nil {
		metadata["expected_ledger_count"] = expectedCount
	}
	result := Object{
		"schema_version": "0.1",
		"provider":       provider,
		"surface":        surface,
		"model": Object{
			"requested":        model,
			"returned":         model,
			"billed":           model,
			"alias_resolution": "none",
		},
		"currency":          "USD",
		"components":        components,
		"total":             total,
		"price_sources":     priceSources,
		"applied_discounts": appliedDiscounts,
		"warnings":          warnings,
		"metadata":          metadata,
	}
	if mode == "strict" && len(warnings) > 0 {
		panic(fmt.Sprintf("strict mode cost aggregation failed: %s", asString(asObject(warnings[0])["code"])))
	}
	return result
}

func getNumber(object Object, keys ...string) any {
	var current any = object
	for _, key := range keys {
		if current == nil {
			return json.Number("0")
		}
		current = asObject(current)[key]
	}
	if current == nil {
		return json.Number("0")
	}
	return current
}

func positiveComponent(name string, quantity any, unit string, sourcePath string) any {
	if rat(quantity).Sign() <= 0 {
		return nil
	}
	return Object{
		"name":        name,
		"quantity":    numberString(quantity),
		"unit":        unit,
		"source_path": sourcePath,
	}
}

func compactComponents(values []any) []any {
	result := []any{}
	for _, value := range values {
		if value != nil {
			result = append(result, value)
		}
	}
	return result
}

func baseUsageLedger(provider string, surface string, requestedModel string, returnedModel string, components []any, rawUsage Object) Object {
	model := returnedModel
	if model == "" {
		model = requestedModel
	}
	return Object{
		"schema_version": "0.1",
		"provider":       provider,
		"surface":        surface,
		"model": Object{
			"requested":        requestedModel,
			"returned":         returnedModel,
			"billed":           model,
			"alias_resolution": "none",
		},
		"components": components,
		"raw_usage":  rawUsage,
	}
}

var openAICompatibleChatProviders = map[string]string{
	"openai.chat_completions":       "openai",
	"openrouter.chat_completions":   "openrouter",
	"groq.chat_completions":         "groq",
	"xai.chat_completions":          "xai",
	"mistral.chat_completions":      "mistral",
	"deepseek.chat_completions":     "deepseek",
	"azure.openai.chat_completions": "azure",
	"huggingface.chat_completions":  "huggingface",
}

func isOpenAICompatibleChatSurface(surface string) bool {
	_, ok := openAICompatibleChatProviders[surface]
	return ok
}

func providerForOpenAICompatibleChat(surface string) string {
	provider := openAICompatibleChatProviders[surface]
	if provider == "" {
		return "openai"
	}
	return provider
}

func openAICompatibleCachedInput(usage Object) (any, string) {
	promptDetails := asObject(usage["prompt_tokens_details"])
	if _, ok := promptDetails["cached_tokens"]; ok {
		return getNumber(usage, "prompt_tokens_details", "cached_tokens"), "$.usage.prompt_tokens_details.cached_tokens"
	}
	if _, ok := usage["prompt_cache_hit_tokens"]; ok {
		return getNumber(usage, "prompt_cache_hit_tokens"), "$.usage.prompt_cache_hit_tokens"
	}
	return json.Number("0"), "$.usage.prompt_tokens_details.cached_tokens"
}

func openAICompatibleReasoningOutput(usage Object) (any, string) {
	completionDetails := asObject(usage["completion_tokens_details"])
	if _, ok := completionDetails["reasoning_tokens"]; ok {
		return getNumber(usage, "completion_tokens_details", "reasoning_tokens"), "$.usage.completion_tokens_details.reasoning_tokens"
	}
	outputDetails := asObject(usage["output_tokens_details"])
	if _, ok := outputDetails["reasoning_tokens"]; ok {
		return getNumber(usage, "output_tokens_details", "reasoning_tokens"), "$.usage.output_tokens_details.reasoning_tokens"
	}
	return json.Number("0"), "$.usage.completion_tokens_details.reasoning_tokens"
}

// ExtractUsageLedger normalizes a raw provider response into the canonical usage
// ledger shape for supported surfaces.
//
// Supported prototype surfaces include OpenAI Responses, OpenAI-compatible chat
// completions, Anthropic Messages, Cohere Chat, Gemini generateContent, and
// AWS Bedrock Converse.
func ExtractUsageLedger(response Object, options Object) Object {
	adapter := asString(options["adapter"])
	if adapter == "" {
		adapter = asString(options["framework"])
	}
	switch adapter {
	case "langchain.chat_message":
		return extractLangChainChatUsage(response, options)
	case "vercel_ai_sdk.generate_text":
		return extractVercelAISDKUsage(response, options)
	case "llamaindex.token_counter":
		return extractLlamaIndexTokenCounterUsage(response, options)
	case "haystack.generator_result":
		return extractHaystackGeneratorUsage(response, options)
	case "litellm.proxy_response":
		return extractLiteLLMProxyResponseUsage(response, options)
	case "ag2.usage_summary":
		return extractAG2UsageSummaryUsage(response, options)
	}

	surface := asString(options["surface"])
	switch surface {
	case "openai.responses":
		return extractOpenAIResponsesUsage(response, options)
	case "openai.chat_completions":
		return extractOpenAIChatCompletionsUsage(response, options)
	case "anthropic.messages":
		return extractAnthropicMessagesUsage(response, options)
	case "google.gemini.generate_content", "vertex.gemini.generate_content":
		return extractGeminiGenerateContentUsage(response, options)
	case "aws.bedrock.converse":
		return extractBedrockConverseUsage(response, options)
	case "cohere.chat":
		return extractCohereChatUsage(response, options)
	default:
		if isOpenAICompatibleChatSurface(surface) {
			return extractOpenAICompatibleChatCompletionsUsage(response, options)
		}
		panic(fmt.Sprintf("unsupported surface: %s", surface))
	}
}

func unsupportedSurfaceLedger(response Object, options Object) Object {
	surface := asString(options["surface"])
	if surface == "" {
		surface = "unknown"
	}
	provider := asString(options["provider"])
	if provider == "" {
		provider = "unknown"
	}
	model := asString(options["model"])
	if model == "" {
		model = asString(response["model"])
	}
	if model == "" {
		model = "unknown"
	}
	return Object{
		"schema_version": "0.1",
		"provider":       provider,
		"surface":        surface,
		"model": Object{
			"requested":        model,
			"returned":         asString(response["model"]),
			"billed":           model,
			"alias_resolution": "unknown",
		},
		"currency":          "USD",
		"components":        []any{},
		"total":             "0",
		"price_sources":     []any{},
		"applied_discounts": []any{},
		"warnings": []any{
			Object{
				"code":    "unknown_surface",
				"message": fmt.Sprintf("Unsupported surface: %s.", surface),
			},
		},
	}
}

func openAIResponsesPayload(response Object) Object {
	if asString(response["type"]) == "response.completed" {
		nested := asObject(response["response"])
		if len(nested) > 0 {
			return nested
		}
	}
	return response
}

func extractOpenAIResponsesUsage(response Object, options Object) Object {
	response = openAIResponsesPayload(response)
	usage := asObject(response["usage"])
	cachedInput := getNumber(usage, "input_tokens_details", "cached_tokens")
	reasoning := getNumber(usage, "output_tokens_details", "reasoning_tokens")
	input := getNumber(usage, "input_tokens")
	output := getNumber(usage, "output_tokens")
	toolComponents := []any{}
	for _, rawItem := range asSlice(response["output"]) {
		item := asObject(rawItem)
		switch asString(item["type"]) {
		case "web_search_call":
			toolComponents = append(toolComponents, positiveComponent("web_search_units", "1", "search", "$.output[*].type"))
		case "file_search_call":
			toolComponents = append(toolComponents, positiveComponent("file_search_units", "1", "call", "$.output[*].type"))
		case "code_interpreter_call":
			toolComponents = append(toolComponents, positiveComponent("code_interpreter_call_units", "1", "call", "$.output[*].type"))
		}
	}
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	requestedModel := asString(options["model"])
	if requestedModel == "" {
		requestedModel = asString(response["model"])
	}

	components := []any{
		positiveComponent("input_uncached_tokens", subtract(input, cachedInput), "token", "$.usage.input_tokens"),
		positiveComponent("input_cache_read_tokens", cachedInput, "token", "$.usage.input_tokens_details.cached_tokens"),
		positiveComponent("output_text_tokens", subtract(output, reasoning), "token", "$.usage.output_tokens"),
		positiveComponent("output_reasoning_tokens", reasoning, "token", "$.usage.output_tokens_details.reasoning_tokens"),
	}
	components = append(components, toolComponents...)
	return baseUsageLedger(provider, "openai.responses", requestedModel, asString(response["model"]), compactComponents(components), usage)
}

func extractOpenAICompatibleChatCompletionsUsage(response Object, options Object) Object {
	usage := asObject(response["usage"])
	cachedInput, cachedSourcePath := openAICompatibleCachedInput(usage)
	reasoning, reasoningSourcePath := openAICompatibleReasoningOutput(usage)
	prompt := getNumber(usage, "prompt_tokens")
	if _, ok := usage["prompt_tokens"]; !ok {
		prompt = add(getNumber(usage, "prompt_cache_hit_tokens"), getNumber(usage, "prompt_cache_miss_tokens"))
	}
	completion := getNumber(usage, "completion_tokens")
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.chat_completions"
	}
	provider := asString(options["provider"])
	if provider == "" {
		provider = providerForOpenAICompatibleChat(surface)
	}
	requestedModel := asString(options["model"])
	if requestedModel == "" {
		requestedModel = asString(response["model"])
	}

	return baseUsageLedger(provider, surface, requestedModel, asString(response["model"]), compactComponents([]any{
		positiveComponent("input_uncached_tokens", subtract(prompt, cachedInput), "token", "$.usage.prompt_tokens"),
		positiveComponent("input_cache_read_tokens", cachedInput, "token", cachedSourcePath),
		positiveComponent("output_text_tokens", subtract(completion, reasoning), "token", "$.usage.completion_tokens"),
		positiveComponent("output_reasoning_tokens", reasoning, "token", reasoningSourcePath),
	}), usage)
}

func extractOpenAIChatCompletionsUsage(response Object, options Object) Object {
	options["provider"] = "openai"
	options["surface"] = "openai.chat_completions"
	return extractOpenAICompatibleChatCompletionsUsage(response, options)
}

func extractOpenRouterChatCompletionsUsage(response Object, options Object) Object {
	options["provider"] = "openrouter"
	options["surface"] = "openrouter.chat_completions"
	return extractOpenAICompatibleChatCompletionsUsage(response, options)
}

func anthropicMessagesPayload(response Object) Object {
	events := asSlice(response["events"])
	if len(events) == 0 {
		return response
	}
	message := Object{}
	usage := Object{}
	for _, rawEvent := range events {
		event := asObject(rawEvent)
		switch asString(event["type"]) {
		case "message_start":
			startMessage := asObject(event["message"])
			if len(startMessage) > 0 {
				for key, value := range startMessage {
					message[key] = value
				}
				for key, value := range asObject(startMessage["usage"]) {
					usage[key] = value
				}
			}
		case "message_delta":
			for key, value := range asObject(event["usage"]) {
				usage[key] = value
			}
			for key, value := range asObject(event["delta"]) {
				message[key] = value
			}
		}
	}
	if len(message) == 0 {
		return response
	}
	message["usage"] = usage
	return message
}

func extractAnthropicMessagesUsage(response Object, options Object) Object {
	response = anthropicMessagesPayload(response)
	usage := asObject(response["usage"])
	cacheWrite := getNumber(usage, "cache_creation_input_tokens")
	cacheWrite1h := getNumber(usage, "cache_creation_input_tokens_1h")
	provider := asString(options["provider"])
	if provider == "" {
		provider = "anthropic"
	}
	requestedModel := asString(options["model"])
	if requestedModel == "" {
		requestedModel = asString(response["model"])
	}

	return baseUsageLedger(provider, "anthropic.messages", requestedModel, asString(response["model"]), compactComponents([]any{
		positiveComponent("input_uncached_tokens", getNumber(usage, "input_tokens"), "token", "$.usage.input_tokens"),
		positiveComponent("input_cache_write_tokens", subtract(cacheWrite, cacheWrite1h), "token", "$.usage.cache_creation_input_tokens"),
		positiveComponent("input_cache_write_1h_tokens", cacheWrite1h, "token", "$.usage.cache_creation_input_tokens_1h"),
		positiveComponent("input_cache_read_tokens", getNumber(usage, "cache_read_input_tokens"), "token", "$.usage.cache_read_input_tokens"),
		positiveComponent("output_text_tokens", getNumber(usage, "output_tokens"), "token", "$.usage.output_tokens"),
	}), usage)
}

var geminiInputModalityComponents = map[string]string{
	"MODALITY_UNSPECIFIED": "input_uncached_tokens",
	"TEXT":                 "input_uncached_tokens",
	"DOCUMENT":             "input_uncached_tokens",
	"IMAGE":                "input_image_tokens",
	"AUDIO":                "input_audio_tokens",
	"VIDEO":                "input_video_tokens",
}

var geminiOutputModalityComponents = map[string]string{
	"MODALITY_UNSPECIFIED": "output_text_tokens",
	"TEXT":                 "output_text_tokens",
	"DOCUMENT":             "output_text_tokens",
	"IMAGE":                "output_image_tokens",
	"AUDIO":                "output_audio_tokens",
	"VIDEO":                "output_video_tokens",
}

var geminiInputComponentOrder = []string{
	"input_uncached_tokens",
	"input_image_tokens",
	"input_audio_tokens",
	"input_video_tokens",
}

var geminiOutputComponentOrder = []string{
	"output_text_tokens",
	"output_image_tokens",
	"output_audio_tokens",
	"output_video_tokens",
}

func addGeminiCount(counts map[string]string, modality string, quantity any) {
	if rat(quantity).Sign() == 0 {
		return
	}
	current := counts[modality]
	if current == "" {
		current = "0"
	}
	counts[modality] = add(current, quantity)
}

func geminiModalityCounts(details any) map[string]string {
	counts := map[string]string{}
	for _, rawDetail := range asSlice(details) {
		detail := asObject(rawDetail)
		modality := strings.ToUpper(asString(detail["modality"]))
		if modality == "" {
			modality = "MODALITY_UNSPECIFIED"
		}
		addGeminiCount(counts, modality, getNumber(detail, "tokenCount"))
	}
	return counts
}

func geminiSumCounts(counts map[string]string) string {
	total := "0"
	for _, quantity := range counts {
		total = add(total, quantity)
	}
	return total
}

func geminiNetInputCounts(promptCounts map[string]string, cacheCounts map[string]string, toolCounts map[string]string) map[string]string {
	modalities := map[string]bool{}
	for modality := range promptCounts {
		modalities[modality] = true
	}
	for modality := range cacheCounts {
		modalities[modality] = true
	}
	for modality := range toolCounts {
		modalities[modality] = true
	}

	counts := map[string]string{}
	for modality := range modalities {
		prompt := promptCounts[modality]
		if prompt == "" {
			prompt = "0"
		}
		cache := cacheCounts[modality]
		if cache == "" {
			cache = "0"
		}
		tool := toolCounts[modality]
		if tool == "" {
			tool = "0"
		}
		counts[modality] = add(subtract(prompt, cache), tool)
	}
	return counts
}

func geminiComponentQuantities(counts map[string]string, modalityComponents map[string]string, fallbackComponent string) map[string]string {
	quantities := map[string]string{}
	for modality, quantity := range counts {
		component := modalityComponents[modality]
		if component == "" {
			component = fallbackComponent
		}
		current := quantities[component]
		if current == "" {
			current = "0"
		}
		quantities[component] = add(current, quantity)
	}
	return quantities
}

func geminiOrderedComponents(quantities map[string]string, order []string, sourcePath string) []any {
	components := []any{}
	for _, component := range order {
		quantity := quantities[component]
		if quantity == "" {
			quantity = "0"
		}
		components = append(components, positiveComponent(component, quantity, "token", sourcePath))
	}
	return components
}

func geminiGenerateContentPayload(response Object) Object {
	chunks := asSlice(response["chunks"])
	if len(chunks) == 0 {
		chunks = asSlice(response["stream"])
	}
	if len(chunks) == 0 {
		return response
	}
	for index := len(chunks) - 1; index >= 0; index-- {
		chunk := asObject(chunks[index])
		if len(asObject(chunk["usageMetadata"])) > 0 {
			return chunk
		}
	}
	for index := len(chunks) - 1; index >= 0; index-- {
		chunk := asObject(chunks[index])
		if len(chunk) > 0 {
			return chunk
		}
	}
	return response
}

func extractGeminiGenerateContentUsage(response Object, options Object) Object {
	response = geminiGenerateContentPayload(response)
	usage := asObject(response["usageMetadata"])
	cachedInput := getNumber(usage, "cachedContentTokenCount")
	prompt := getNumber(usage, "promptTokenCount")
	candidates := getNumber(usage, "candidatesTokenCount")
	thoughts := getNumber(usage, "thoughtsTokenCount")
	promptCounts := geminiModalityCounts(usage["promptTokensDetails"])
	cacheCounts := geminiModalityCounts(usage["cacheTokensDetails"])
	toolCounts := geminiModalityCounts(usage["toolUsePromptTokensDetails"])
	candidateCounts := geminiModalityCounts(usage["candidatesTokensDetails"])
	toolPrompt := getNumber(usage, "toolUsePromptTokenCount")
	if _, hasToolPrompt := usage["toolUsePromptTokenCount"]; !hasToolPrompt {
		toolPrompt = geminiSumCounts(toolCounts)
	}
	toolRemainder := subtract(toolPrompt, geminiSumCounts(toolCounts))
	if rat(toolRemainder).Sign() > 0 {
		addGeminiCount(toolCounts, "TEXT", toolRemainder)
	}

	detailSafeForInput := len(promptCounts) > 0 && (rat(cachedInput).Sign() == 0 || len(cacheCounts) > 0)
	var inputComponents []any
	cacheRead := cachedInput
	if detailSafeForInput {
		inputComponents = geminiOrderedComponents(
			geminiComponentQuantities(
				geminiNetInputCounts(promptCounts, cacheCounts, toolCounts),
				geminiInputModalityComponents,
				"input_uncached_tokens",
			),
			geminiInputComponentOrder,
			"$.usageMetadata.promptTokensDetails",
		)
		if rat(cachedInput).Sign() == 0 {
			cacheRead = geminiSumCounts(cacheCounts)
		}
	} else {
		inputComponents = []any{
			positiveComponent("input_uncached_tokens", add(subtract(prompt, cachedInput), toolPrompt), "token", "$.usageMetadata.promptTokenCount"),
		}
	}

	var outputComponents []any
	if len(candidateCounts) > 0 {
		outputComponents = geminiOrderedComponents(
			geminiComponentQuantities(candidateCounts, geminiOutputModalityComponents, "output_text_tokens"),
			geminiOutputComponentOrder,
			"$.usageMetadata.candidatesTokensDetails",
		)
	} else {
		outputComponents = []any{
			positiveComponent("output_text_tokens", candidates, "token", "$.usageMetadata.candidatesTokenCount"),
		}
	}

	provider := asString(options["provider"])
	if provider == "" {
		provider = "google"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "google.gemini.generate_content"
	}
	requestedModel := asString(options["model"])
	if requestedModel == "" {
		requestedModel = asString(response["modelVersion"])
	}
	returnedModel := asString(response["modelVersion"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}

	components := []any{}
	components = append(components, inputComponents[:1]...)
	components = append(components, positiveComponent("input_cache_read_tokens", cacheRead, "token", "$.usageMetadata.cachedContentTokenCount"))
	components = append(components, inputComponents[1:]...)
	components = append(components, outputComponents[:1]...)
	components = append(components, positiveComponent("output_reasoning_tokens", thoughts, "token", "$.usageMetadata.thoughtsTokenCount"))
	components = append(components, outputComponents[1:]...)

	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents(components), usage)
}

func extractBedrockConverseUsage(response Object, options Object) Object {
	usage := asObject(response["usage"])
	cacheRead := getNumber(usage, "cacheReadInputTokens")
	cacheWrite := getNumber(usage, "cacheWriteInputTokens")
	cacheWrite1h := "0"
	for _, rawDetail := range asSlice(usage["cacheDetails"]) {
		detail := asObject(rawDetail)
		if asString(detail["ttl"]) == "1h" {
			cacheWrite1h = add(cacheWrite1h, getNumber(detail, "inputTokens"))
		}
	}
	provider := asString(options["provider"])
	if provider == "" {
		provider = "bedrock"
	}
	requestedModel := asString(options["model"])
	if requestedModel == "" {
		requestedModel = asString(response["modelId"])
	}
	returnedModel := asString(response["modelId"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}

	return baseUsageLedger(provider, "aws.bedrock.converse", requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", subtract(subtract(getNumber(usage, "inputTokens"), cacheRead), cacheWrite), "token", "$.usage.inputTokens"),
		positiveComponent("input_cache_write_tokens", subtract(cacheWrite, cacheWrite1h), "token", "$.usage.cacheWriteInputTokens"),
		positiveComponent("input_cache_write_1h_tokens", cacheWrite1h, "token", "$.usage.cacheDetails"),
		positiveComponent("input_cache_read_tokens", cacheRead, "token", "$.usage.cacheReadInputTokens"),
		positiveComponent("output_text_tokens", getNumber(usage, "outputTokens"), "token", "$.usage.outputTokens"),
	}), usage)
}

func cohereChatUsagePayload(response Object) (Object, string) {
	usage := asObject(response["usage"])
	if _, ok := usage["billed_units"]; ok {
		return usage, "$.usage"
	}
	return asObject(response["meta"]), "$.meta"
}

func extractCohereChatUsage(response Object, options Object) Object {
	usage, sourceRoot := cohereChatUsagePayload(response)
	billedUnits := asObject(usage["billed_units"])
	provider := asString(options["provider"])
	if provider == "" {
		provider = "cohere"
	}
	requestedModel := asString(options["model"])
	if requestedModel == "" {
		requestedModel = asString(response["model"])
	}
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}

	return baseUsageLedger(provider, "cohere.chat", requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", getNumber(billedUnits, "input_tokens"), "token", sourceRoot+".billed_units.input_tokens"),
		positiveComponent("output_text_tokens", getNumber(billedUnits, "output_tokens"), "token", sourceRoot+".billed_units.output_tokens"),
	}), usage)
}

func extractLangChainChatUsage(response Object, options Object) Object {
	usage := asObject(response["usage_metadata"])
	if len(usage) == 0 {
		usage = asObject(response["usageMetadata"])
	}
	inputDetails := asObject(usage["input_token_details"])
	outputDetails := asObject(usage["output_token_details"])
	cacheRead := getNumber(inputDetails, "cache_read")
	cacheWrite := getNumber(inputDetails, "cache_creation")
	inputTokens := getNumber(usage, "input_tokens")
	outputTokens := getNumber(usage, "output_tokens")
	reasoning := getNumber(outputDetails, "reasoning")
	metadata := asObject(response["response_metadata"])
	provider := asString(options["provider"])
	if provider == "" {
		provider = "unknown"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "framework.langchain.chat"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(metadata["model_name"])
	if returnedModel == "" {
		returnedModel = asString(metadata["model"])
	}
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}

	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", subtract(subtract(inputTokens, cacheRead), cacheWrite), "token", "$.usage_metadata.input_tokens"),
		positiveComponent("input_cache_read_tokens", cacheRead, "token", "$.usage_metadata.input_token_details.cache_read"),
		positiveComponent("input_cache_write_tokens", cacheWrite, "token", "$.usage_metadata.input_token_details.cache_creation"),
		positiveComponent("output_text_tokens", subtract(outputTokens, reasoning), "token", "$.usage_metadata.output_tokens"),
		positiveComponent("output_reasoning_tokens", reasoning, "token", "$.usage_metadata.output_token_details.reasoning"),
	}), usage)
}

func vercelAISDKUsagePayload(response Object) (Object, string) {
	totalUsage := asObject(response["totalUsage"])
	if len(totalUsage) > 0 {
		return totalUsage, "$.totalUsage"
	}
	return asObject(response["usage"]), "$.usage"
}

func extractVercelAISDKUsage(response Object, options Object) Object {
	usage, sourceRoot := vercelAISDKUsagePayload(response)
	inputDetails := asObject(usage["inputTokenDetails"])
	outputDetails := asObject(usage["outputTokenDetails"])
	cacheRead := getNumber(inputDetails, "cacheReadTokens")
	if rat(cacheRead).Sign() == 0 {
		cacheRead = getNumber(usage, "cachedInputTokens")
	}
	cacheWrite := getNumber(inputDetails, "cacheWriteTokens")
	inputTokens := getNumber(usage, "inputTokens")
	uncached := getNumber(inputDetails, "noCacheTokens")
	if rat(uncached).Sign() == 0 {
		uncached = subtract(subtract(inputTokens, cacheRead), cacheWrite)
	}
	outputTokens := getNumber(usage, "outputTokens")
	reasoning := getNumber(outputDetails, "reasoningTokens")
	if rat(reasoning).Sign() == 0 {
		reasoning = getNumber(usage, "reasoningTokens")
	}
	textTokens := getNumber(outputDetails, "textTokens")
	if rat(textTokens).Sign() == 0 {
		textTokens = subtract(outputTokens, reasoning)
	}
	modelMetadata := asObject(response["model"])
	responseMetadata := asObject(response["response"])
	provider := asString(options["provider"])
	if provider == "" {
		provider = asString(modelMetadata["provider"])
	}
	if provider == "" {
		provider = "unknown"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "framework.vercel_ai_sdk"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(responseMetadata["modelId"])
	if returnedModel == "" {
		returnedModel = asString(modelMetadata["modelId"])
	}
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}

	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", uncached, "token", sourceRoot+".inputTokenDetails.noCacheTokens"),
		positiveComponent("input_cache_read_tokens", cacheRead, "token", sourceRoot+".inputTokenDetails.cacheReadTokens"),
		positiveComponent("input_cache_write_tokens", cacheWrite, "token", sourceRoot+".inputTokenDetails.cacheWriteTokens"),
		positiveComponent("output_text_tokens", textTokens, "token", sourceRoot+".outputTokenDetails.textTokens"),
		positiveComponent("output_reasoning_tokens", reasoning, "token", sourceRoot+".outputTokenDetails.reasoningTokens"),
	}), usage)
}

func extractLlamaIndexTokenCounterUsage(response Object, options Object) Object {
	promptTokens := "0"
	completionTokens := "0"
	events := asSlice(response["llm_token_counts"])
	if len(events) > 0 {
		for _, rawEvent := range events {
			event := asObject(rawEvent)
			promptTokens = add(promptTokens, getNumber(event, "prompt_token_count"))
			completionTokens = add(completionTokens, getNumber(event, "completion_token_count"))
		}
	} else {
		promptTokens = numberString(getNumber(response, "prompt_llm_token_count"))
		completionTokens = numberString(getNumber(response, "completion_llm_token_count"))
	}
	provider := asString(options["provider"])
	if provider == "" {
		provider = "unknown"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "framework.llamaindex.token_counter"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}

	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", promptTokens, "token", "$.llm_token_counts[*].prompt_token_count"),
		positiveComponent("output_text_tokens", completionTokens, "token", "$.llm_token_counts[*].completion_token_count"),
	}), response)
}

func haystackUsagePayload(response Object) (Object, Object, string) {
	replies := asSlice(response["replies"])
	if len(replies) > 0 {
		reply := asObject(replies[0])
		metadata := asObject(reply["_meta"])
		if len(metadata) == 0 {
			metadata = asObject(reply["meta"])
		}
		if len(metadata) > 0 {
			return asObject(metadata["usage"]), metadata, "$.replies[0]._meta.usage"
		}
	}
	metaItems := asSlice(response["meta"])
	if len(metaItems) > 0 {
		metadata := asObject(metaItems[0])
		return asObject(metadata["usage"]), metadata, "$.meta[0].usage"
	}
	metadata := asObject(response["meta"])
	if len(metadata) > 0 {
		return asObject(metadata["usage"]), metadata, "$.meta.usage"
	}
	return asObject(response["usage"]), response, "$.usage"
}

func extractHaystackGeneratorUsage(response Object, options Object) Object {
	usage, metadata, sourceRoot := haystackUsagePayload(response)
	cachedInput, cachedSourcePath := openAICompatibleCachedInput(usage)
	reasoning, reasoningSourcePath := openAICompatibleReasoningOutput(usage)
	prompt := getNumber(usage, "prompt_tokens")
	if _, ok := usage["prompt_tokens"]; !ok {
		prompt = add(getNumber(usage, "prompt_cache_hit_tokens"), getNumber(usage, "prompt_cache_miss_tokens"))
	}
	completion := getNumber(usage, "completion_tokens")
	provider := asString(options["provider"])
	if provider == "" {
		provider = "unknown"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "framework.haystack.generator"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(metadata["model"])
	if returnedModel == "" {
		returnedModel = asString(response["model"])
	}
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}

	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", subtract(prompt, cachedInput), "token", sourceRoot+".prompt_tokens"),
		positiveComponent("input_cache_read_tokens", cachedInput, "token", strings.Replace(cachedSourcePath, "$.usage", sourceRoot, 1)),
		positiveComponent("output_text_tokens", subtract(completion, reasoning), "token", sourceRoot+".completion_tokens"),
		positiveComponent("output_reasoning_tokens", reasoning, "token", strings.Replace(reasoningSourcePath, "$.usage", sourceRoot, 1)),
	}), usage)
}

func extractLiteLLMProxyResponseUsage(response Object, options Object) Object {
	hidden := asObject(response["_hidden_params"])
	if len(hidden) == 0 {
		hidden = asObject(response["hidden_params"])
	}
	if asString(options["provider"]) == "" {
		provider := asString(hidden["custom_llm_provider"])
		if provider == "" {
			provider = asString(hidden["litellm_provider"])
		}
		if provider != "" {
			options["provider"] = provider
		}
	}
	return extractOpenAICompatibleChatCompletionsUsage(response, options)
}

func ag2UsageSummaryPayload(response Object, options Object) (Object, string) {
	mode := asString(options["ag2_usage_mode"])
	if mode == "" {
		mode = asString(options["usage_mode"])
	}
	if mode == "" {
		mode = "actual"
	}
	excluding := asObject(response["usage_excluding_cached_inference"])
	including := asObject(response["usage_including_cached_inference"])
	if len(excluding) > 0 || len(including) > 0 {
		switch mode {
		case "total", "including_cached", "usage_including_cached_inference":
			return including, "usage_including_cached_inference"
		default:
			return excluding, "usage_excluding_cached_inference"
		}
	}
	return response, mode
}

func ag2ModelUsage(summary Object, requestedModel string) (string, Object) {
	if requestedModel != "" {
		usage := asObject(summary[requestedModel])
		if len(usage) > 0 {
			return requestedModel, usage
		}
	}
	keys := make([]string, 0, len(summary))
	for key := range summary {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		if key == "total_cost" {
			continue
		}
		usage := asObject(summary[key])
		if len(usage) > 0 {
			return key, usage
		}
	}
	if requestedModel != "" {
		return requestedModel, Object{}
	}
	return "unknown", Object{}
}

func extractAG2UsageSummaryUsage(response Object, options Object) Object {
	summary, mode := ag2UsageSummaryPayload(response, options)
	returnedModel, modelUsage := ag2ModelUsage(summary, asString(options["model"]))
	provider := asString(options["provider"])
	if provider == "" {
		provider = "unknown"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "framework.ag2.usage_summary"
	}
	requestedModel := asString(options["model"])
	if requestedModel == "" {
		requestedModel = returnedModel
	}

	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", getNumber(modelUsage, "prompt_tokens"), "token", "$."+mode+"."+returnedModel+".prompt_tokens"),
		positiveComponent("output_text_tokens", getNumber(modelUsage, "completion_tokens"), "token", "$."+mode+"."+returnedModel+".completion_tokens"),
	}), Object{
		"mode":        mode,
		"summary":     summary,
		"model_usage": modelUsage,
	})
}

func addPriceComponent(components *[]any, usageComponent string, unit string, amount any, per string, extra Object) {
	if amount == nil {
		return
	}
	component := Object{
		"usage_component": usageComponent,
		"unit":            unit,
		"price":           Object{"amount": numberString(amount), "currency": "USD", "per": per},
	}
	for key, value := range extra {
		component[key] = value
	}
	*components = append(*components, component)
}

// PriceCardsFromLlmPrices maps Simon Willison llm-prices data into canonical
// price cards.
func PriceCardsFromLlmPrices(data Object) []any {
	updatedAt := asString(data["updated_at"])
	if updatedAt == "" {
		updatedAt = "1970-01-01"
	}
	cards := []any{}
	for _, rawPrice := range asSlice(data["prices"]) {
		price := asObject(rawPrice)
		components := []any{
			Object{
				"usage_component": "input_uncached_tokens",
				"unit":            "token",
				"price":           Object{"amount": numberString(price["input"]), "currency": "USD", "per": "1000000"},
			},
			Object{
				"usage_component": "output_text_tokens",
				"unit":            "token",
				"price":           Object{"amount": numberString(price["output"]), "currency": "USD", "per": "1000000"},
			},
		}
		if price["input_cached"] != nil {
			components = append(components, Object{
				"usage_component": "input_cache_read_tokens",
				"unit":            "token",
				"price":           Object{"amount": numberString(price["input_cached"]), "currency": "USD", "per": "1000000"},
			})
		}

		aliases := []any{}
		if name := asString(price["name"]); name != "" {
			aliases = append(aliases, name)
		}
		cards = append(cards, Object{
			"schema_version": "0.1",
			"id":             fmt.Sprintf("%s:%s:llm-prices", asString(price["vendor"]), asString(price["id"])),
			"provider":       asString(price["vendor"]),
			"model":          asString(price["id"]),
			"aliases":        aliases,
			"effective":      Object{"from": price["from_date"], "to": price["to_date"]},
			"components":     components,
			"source": Object{
				"name":         "llm-prices",
				"url":          "https://www.llm-prices.com/current-v1.json",
				"retrieved_at": updatedAt + "T00:00:00Z",
			},
		})
	}
	return cards
}

// PriceCardsFromLiteLLM maps LiteLLM model pricing data into canonical price
// cards.
func PriceCardsFromLiteLLM(data Object) []any {
	updatedAt := asString(data["updated_at"])
	if updatedAt == "" {
		updatedAt = "1970-01-01"
	}
	cards := []any{}
	for model, rawConfig := range data {
		if model == "sample_spec" || model == "updated_at" {
			continue
		}
		config, ok := rawConfig.(map[string]any)
		if !ok {
			continue
		}
		provider := asString(config["litellm_provider"])
		if provider == "" {
			provider = "unknown"
		}
		components := []any{}
		addPriceComponent(&components, "input_uncached_tokens", "token", config["input_cost_per_token"], "1", nil)
		addPriceComponent(&components, "output_text_tokens", "token", config["output_cost_per_token"], "1", nil)
		addPriceComponent(&components, "input_cache_read_tokens", "token", config["cache_read_input_token_cost"], "1", nil)
		addPriceComponent(&components, "input_cache_write_tokens", "token", config["cache_creation_input_token_cost"], "1", nil)
		addPriceComponent(&components, "input_cache_write_1h_tokens", "token", config["cache_creation_input_token_cost_1h"], "1", nil)
		reasoning := config["output_cost_per_reasoning_token"]
		if reasoning == nil {
			reasoning = config["output_cost_per_token"]
		}
		addPriceComponent(&components, "output_reasoning_tokens", "token", reasoning, "1", nil)
		if len(components) == 0 {
			continue
		}
		cards = append(cards, Object{
			"schema_version": "0.1",
			"id":             fmt.Sprintf("%s:%s:litellm", provider, model),
			"provider":       provider,
			"model":          model,
			"components":     components,
			"source": Object{
				"name":         "litellm",
				"url":          "https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json",
				"retrieved_at": updatedAt + "T00:00:00Z",
			},
		})
	}
	return cards
}

// PriceCardsFromPortkey maps Portkey-style model pricing data into canonical
// price cards.
func PriceCardsFromPortkey(data Object) []any {
	updatedAt := asString(data["updated_at"])
	if updatedAt == "" {
		updatedAt = "1970-01-01"
	}
	provider := asString(data["provider"])
	if provider == "" {
		provider = "unknown"
	}
	cards := []any{}
	for model, rawEntry := range asObject(data["models"]) {
		entry := asObject(rawEntry)
		pricing := asObject(entry["pricing"])
		if len(pricing) == 0 {
			pricing = asObject(entry["pay_as_you_go"])
		}
		components := []any{}
		if pricing["request_token"] != nil {
			addPriceComponent(&components, "input_uncached_tokens", "token", multiplyDivide(pricing["request_token"], "1", "100"), "1", nil)
		}
		if pricing["response_token"] != nil {
			addPriceComponent(&components, "output_text_tokens", "token", multiplyDivide(pricing["response_token"], "1", "100"), "1", nil)
		}
		if pricing["cache_read_input_token"] != nil {
			addPriceComponent(&components, "input_cache_read_tokens", "token", multiplyDivide(pricing["cache_read_input_token"], "1", "100"), "1", nil)
		}
		if pricing["cache_write_input_token"] != nil {
			addPriceComponent(&components, "input_cache_write_tokens", "token", multiplyDivide(pricing["cache_write_input_token"], "1", "100"), "1", nil)
		}
		additional := asObject(pricing["additional_units"])
		if additional["thinking_token"] != nil {
			addPriceComponent(&components, "output_reasoning_tokens", "token", multiplyDivide(additional["thinking_token"], "1", "100"), "1", nil)
		}
		if additional["web_search"] != nil {
			addPriceComponent(&components, "web_search_units", "search", multiplyDivide(additional["web_search"], "1", "100"), "1", nil)
		}
		if len(components) == 0 {
			continue
		}
		cards = append(cards, Object{
			"schema_version": "0.1",
			"id":             fmt.Sprintf("%s:%s:portkey", provider, model),
			"provider":       provider,
			"model":          model,
			"components":     components,
			"source": Object{
				"name":         "portkey",
				"url":          "https://github.com/Portkey-AI/models",
				"retrieved_at": updatedAt + "T00:00:00Z",
			},
		})
	}
	return cards
}

func openRouterPricingTiers(pricing any) []Object {
	tiers := []Object{}
	switch typed := pricing.(type) {
	case []any:
		for _, rawTier := range typed {
			if tier, ok := rawTier.(map[string]any); ok {
				tiers = append(tiers, tier)
			}
		}
	case map[string]any:
		tiers = append(tiers, typed)
	}
	return tiers
}

func openRouterTierConditions(tiers []Object, index int) Object {
	tier := tiers[index]
	conditions := Object{}
	if tier["min_context"] != nil {
		conditions["min_total_input_tokens"] = numberString(tier["min_context"])
	}
	if tier["min_context"] == nil {
		for _, candidate := range tiers[index+1:] {
			if candidate["min_context"] != nil {
				conditions["max_total_input_tokens"] = subtract(candidate["min_context"], "1")
				break
			}
		}
	}
	if len(conditions) == 0 {
		return Object{}
	}
	return Object{"conditions": conditions}
}

func thresholdTierConditions(tiers []Object, index int) Object {
	tier := tiers[index]
	conditions := Object{}
	if tier["threshold"] != nil && rat(tier["threshold"]).Sign() > 0 {
		conditions["min_total_input_tokens"] = numberString(tier["threshold"])
	}
	for _, candidate := range tiers[index+1:] {
		if candidate["threshold"] != nil {
			conditions["max_total_input_tokens"] = subtract(candidate["threshold"], "1")
			break
		}
	}
	if len(conditions) == 0 {
		return Object{}
	}
	return Object{"conditions": conditions}
}

// PriceCardsFromOpenRouterModels maps OpenRouter /api/v1/models data into
// canonical price cards.
func PriceCardsFromOpenRouterModels(data Object) []any {
	updatedAt := asString(data["updated_at"])
	if updatedAt == "" {
		updatedAt = "1970-01-01"
	}
	provider := "openrouter"
	cards := []any{}
	for _, rawModel := range asSlice(data["data"]) {
		model := asObject(rawModel)
		modelID := asString(model["id"])
		if modelID == "" {
			modelID = asString(model["canonical_slug"])
		}
		if modelID == "" {
			continue
		}
		tiers := openRouterPricingTiers(model["pricing"])
		components := []any{}
		for index, tier := range tiers {
			tokenConditions := openRouterTierConditions(tiers, index)
			addPriceComponent(&components, "input_uncached_tokens", "token", tier["prompt"], "1", tokenConditions)
			addPriceComponent(&components, "output_text_tokens", "token", tier["completion"], "1", tokenConditions)
			addPriceComponent(&components, "input_cache_read_tokens", "token", tier["input_cache_read"], "1", tokenConditions)
			addPriceComponent(&components, "input_cache_write_tokens", "token", tier["input_cache_write"], "1", tokenConditions)
			addPriceComponent(&components, "output_reasoning_tokens", "token", tier["internal_reasoning"], "1", tokenConditions)
			if index == 0 {
				addPriceComponent(&components, "input_image_units", "image", tier["image"], "1", nil)
				addPriceComponent(&components, "request_units", "request", tier["request"], "1", nil)
				addPriceComponent(&components, "web_search_units", "search", tier["web_search"], "1", nil)
			}
		}
		if len(components) == 0 {
			continue
		}
		aliases := []any{}
		if canonicalSlug := asString(model["canonical_slug"]); canonicalSlug != "" && canonicalSlug != modelID {
			aliases = append(aliases, canonicalSlug)
		}
		if name := asString(model["name"]); name != "" && name != modelID {
			aliases = append(aliases, name)
		}
		card := Object{
			"schema_version": "0.1",
			"id":             fmt.Sprintf("%s:%s:openrouter-models", provider, modelID),
			"provider":       provider,
			"model":          modelID,
			"aliases":        aliases,
			"components":     components,
			"source": Object{
				"name":         "openrouter",
				"url":          "https://openrouter.ai/api/v1/models",
				"retrieved_at": updatedAt + "T00:00:00Z",
			},
		}
		if expirationDate := asString(model["expiration_date"]); expirationDate != "" {
			card["effective"] = Object{"to": expirationDate}
		}
		cards = append(cards, card)
	}
	return cards
}

func sourceInfo(data Object, defaultName string, defaultURL string) Object {
	source := Object{}
	if rawSource, ok := data["source"].(map[string]any); ok {
		source = rawSource
	}
	retrievedAt := asString(source["retrieved_at"])
	if retrievedAt == "" {
		retrievedAt = asString(source["retrievedAt"])
	}
	if retrievedAt == "" {
		retrievedAt = asString(data["retrieved_at"])
	}
	if retrievedAt == "" {
		retrievedAt = asString(data["retrievedAt"])
	}
	if retrievedAt == "" {
		updatedAt := asString(data["updated_at"])
		if updatedAt == "" {
			updatedAt = "1970-01-01"
		}
		retrievedAt = updatedAt + "T00:00:00Z"
	}
	name := asString(source["name"])
	if name == "" {
		name = defaultName
	}
	url := asString(source["url"])
	if url == "" {
		url = defaultURL
	}
	info := Object{"name": name, "url": url, "retrieved_at": retrievedAt}
	if version := asString(source["version"]); version != "" {
		info["version"] = version
	}
	if license := asString(source["license"]); license != "" {
		info["license"] = license
	}
	return info
}

func componentAmount(entry Object, keys ...string) any {
	prices := Object{}
	if rawPrices, ok := entry["prices"].(map[string]any); ok {
		prices = rawPrices
	}
	pricing := Object{}
	if rawPricing, ok := entry["pricing"].(map[string]any); ok {
		pricing = rawPricing
	}
	for _, key := range keys {
		if value, ok := entry[key]; ok {
			return value
		}
		if value, ok := prices[key]; ok {
			return value
		}
		if value, ok := pricing[key]; ok {
			return value
		}
	}
	return nil
}

// PriceCardsFromUserPricing maps user-owned compact pricing data into
// canonical price cards. Already-canonical price_cards are returned unchanged.
func PriceCardsFromUserPricing(data Object) []any {
	if rawCards, ok := data["price_cards"].([]any); ok {
		return rawCards
	}
	if rawCards, ok := data["priceCards"].([]any); ok {
		return rawCards
	}
	source := sourceInfo(data, "user-pricing", "file://user-pricing")
	providerDefault := asString(data["provider"])
	if providerDefault == "" {
		providerDefault = "user"
	}
	surfaceDefault := asString(data["surface"])
	serviceTierDefault := asString(data["service_tier"])
	if serviceTierDefault == "" {
		serviceTierDefault = asString(data["serviceTier"])
	}
	regionDefault := asString(data["region"])
	perDefault := numberString(data["per"])
	if perDefault == "0" {
		perDefault = "1000000"
	}
	cards := []any{}
	for _, rawEntry := range asSlice(data["models"]) {
		entry := asObject(rawEntry)
		if _, ok := entry["components"].([]any); ok && asString(entry["provider"]) != "" && (asString(entry["model"]) != "" || asString(entry["id"]) != "") {
			card := Object{}
			for key, value := range entry {
				card[key] = value
			}
			if card["schema_version"] == nil {
				card["schema_version"] = "0.1"
			}
			if asString(card["model"]) == "" {
				card["model"] = asString(card["id"])
			}
			if card["source"] == nil {
				card["source"] = source
			}
			cards = append(cards, card)
			continue
		}

		model := asString(entry["model"])
		if model == "" {
			model = asString(entry["id"])
		}
		if model == "" {
			continue
		}
		provider := asString(entry["provider"])
		if provider == "" {
			provider = providerDefault
		}
		per := numberString(entry["per"])
		if per == "0" {
			per = perDefault
		}
		components := []any{}
		addPriceComponent(&components, "input_uncached_tokens", "token", componentAmount(entry, "input", "input_uncached", "input_uncached_tokens"), per, nil)
		addPriceComponent(&components, "input_cache_read_tokens", "token", componentAmount(entry, "cached_input", "input_cached", "cache_read", "input_cache_read"), per, nil)
		addPriceComponent(&components, "input_cache_write_tokens", "token", componentAmount(entry, "cache_write", "input_cache_write"), per, nil)
		addPriceComponent(&components, "input_cache_write_1h_tokens", "token", componentAmount(entry, "cache_write_1h", "input_cache_write_1h"), per, nil)
		addPriceComponent(&components, "output_text_tokens", "token", componentAmount(entry, "output", "completion", "output_text"), per, nil)
		addPriceComponent(&components, "output_reasoning_tokens", "token", componentAmount(entry, "reasoning", "thinking", "output_reasoning"), per, nil)
		addPriceComponent(&components, "request_units", "request", componentAmount(entry, "request", "per_request"), "1", nil)
		addPriceComponent(&components, "web_search_units", "search", componentAmount(entry, "web_search"), "1", nil)
		if len(components) == 0 {
			continue
		}
		cardID := asString(entry["price_card_id"])
		if cardID == "" {
			cardID = asString(entry["priceCardId"])
		}
		if cardID == "" {
			cardID = fmt.Sprintf("%s:%s:user-pricing", provider, model)
		}
		card := Object{
			"schema_version": "0.1",
			"id":             cardID,
			"provider":       provider,
			"model":          model,
			"aliases":        asSlice(entry["aliases"]),
			"components":     components,
			"source":         source,
		}
		surface := asString(entry["surface"])
		if surface == "" {
			surface = surfaceDefault
		}
		if surface != "" {
			card["surface"] = surface
		}
		serviceTier := asString(entry["service_tier"])
		if serviceTier == "" {
			serviceTier = asString(entry["serviceTier"])
		}
		if serviceTier == "" {
			serviceTier = serviceTierDefault
		}
		if serviceTier != "" {
			card["service_tier"] = serviceTier
		}
		region := asString(entry["region"])
		if region == "" {
			region = regionDefault
		}
		if region != "" {
			card["region"] = region
		}
		if effective, ok := entry["effective"].(map[string]any); ok {
			card["effective"] = effective
		}
		cards = append(cards, card)
	}
	return cards
}

func heliconeEndpointItems(data Object) []Object {
	endpoints := data
	if rawEndpoints, ok := data["endpoints"].(map[string]any); ok {
		endpoints = rawEndpoints
	}
	items := []Object{}
	for _, rawEntry := range endpoints {
		if entry, ok := rawEntry.(map[string]any); ok {
			items = append(items, entry)
		}
	}
	return items
}

func heliconePricingTiers(pricing any) []Object {
	tiers := []Object{}
	switch typed := pricing.(type) {
	case []any:
		for _, rawTier := range typed {
			if tier, ok := rawTier.(map[string]any); ok {
				tiers = append(tiers, tier)
			}
		}
	case map[string]any:
		tiers = append(tiers, typed)
	}
	sort.SliceStable(tiers, func(i, j int) bool {
		return rat(tiers[i]["threshold"]).Cmp(rat(tiers[j]["threshold"])) < 0
	})
	return tiers
}

func heliconeAddModalityComponents(components *[]any, tier Object, modality string, conditions Object) {
	pricing, ok := tier[modality].(map[string]any)
	if !ok {
		return
	}
	names := map[string][2]string{
		"image": {"input_image_tokens", "output_image_tokens"},
		"audio": {"input_audio_tokens", "output_audio_tokens"},
		"video": {"input_video_tokens", "output_video_tokens"},
	}
	componentNames, ok := names[modality]
	if !ok {
		return
	}
	addPriceComponent(components, componentNames[0], "token", pricing["input"], "1", conditions)
	addPriceComponent(components, componentNames[1], "token", pricing["output"], "1", conditions)
}

// PriceCardsFromHelicone maps Helicone model-registry endpoint configs into
// canonical price cards.
func PriceCardsFromHelicone(data Object) []any {
	source := sourceInfo(data, "helicone", "https://github.com/Helicone/helicone/tree/main/packages/cost")
	cards := []any{}
	for _, endpoint := range heliconeEndpointItems(data) {
		model := asString(endpoint["providerModelId"])
		provider := asString(endpoint["provider"])
		if model == "" || provider == "" {
			continue
		}
		tiers := heliconePricingTiers(endpoint["pricing"])
		components := []any{}
		for index, tier := range tiers {
			conditions := thresholdTierConditions(tiers, index)
			inputPrice := tier["input"]
			addPriceComponent(&components, "input_uncached_tokens", "token", inputPrice, "1", conditions)
			addPriceComponent(&components, "output_text_tokens", "token", tier["output"], "1", conditions)
			cacheMultipliers := Object{}
			if rawCacheMultipliers, ok := tier["cacheMultipliers"].(map[string]any); ok {
				cacheMultipliers = rawCacheMultipliers
			}
			if inputPrice != nil {
				if cacheMultipliers["cachedInput"] != nil {
					addPriceComponent(&components, "input_cache_read_tokens", "token", multiplyDivide(inputPrice, cacheMultipliers["cachedInput"], "1"), "1", conditions)
				}
				if cacheMultipliers["write5m"] != nil {
					addPriceComponent(&components, "input_cache_write_tokens", "token", multiplyDivide(inputPrice, cacheMultipliers["write5m"], "1"), "1", conditions)
				}
				if cacheMultipliers["write1h"] != nil {
					addPriceComponent(&components, "input_cache_write_1h_tokens", "token", multiplyDivide(inputPrice, cacheMultipliers["write1h"], "1"), "1", conditions)
				}
			}
			addPriceComponent(&components, "output_reasoning_tokens", "token", tier["thinking"], "1", conditions)
			if index == 0 {
				addPriceComponent(&components, "request_units", "request", tier["request"], "1", nil)
				addPriceComponent(&components, "web_search_units", "search", tier["web_search"], "1", nil)
			}
			for _, modality := range []string{"image", "audio", "video"} {
				heliconeAddModalityComponents(&components, tier, modality, conditions)
			}
		}
		if len(components) == 0 {
			continue
		}
		aliases := []any{}
		for _, rawAlias := range asSlice(endpoint["providerModelIdAliases"]) {
			if alias := asString(rawAlias); alias != "" && alias != model {
				aliases = append(aliases, alias)
			}
		}
		cards = append(cards, Object{
			"schema_version": "0.1",
			"id":             fmt.Sprintf("%s:%s:helicone", provider, model),
			"provider":       provider,
			"model":          model,
			"aliases":        aliases,
			"components":     components,
			"source":         source,
			"metadata": Object{
				"author":                endpoint["author"],
				"context_length":        endpoint["contextLength"],
				"max_completion_tokens": endpoint["maxCompletionTokens"],
				"ptb_enabled":           endpoint["ptbEnabled"],
			},
		})
	}
	return cards
}

// FromResponse extracts usage from a raw provider response and immediately
// calculates a cost ledger from the supplied price cards and discount policies.
func FromResponse(response Object, options Object, priceCards []any, discountPolicies []any) Object {
	mode := asString(options["mode"])
	if mode == "" {
		mode = "compatibility"
	}
	surface := asString(options["surface"])
	if surface != "openai.responses" &&
		surface != "anthropic.messages" &&
		surface != "google.gemini.generate_content" &&
		surface != "vertex.gemini.generate_content" &&
		surface != "aws.bedrock.converse" &&
		surface != "cohere.chat" &&
		!isOpenAICompatibleChatSurface(surface) {
		if mode == "strict" {
			panic(fmt.Sprintf("unsupported surface: %s", surface))
		}
		return unsupportedSurfaceLedger(response, options)
	}
	usageLedger := ExtractUsageLedger(response, options)
	options["mode"] = mode
	return CalculateCostWithOptions(usageLedger, priceCards, discountPolicies, options)
}

// FromLangChainMessage prices a LangChain AIMessage-like object by reading its
// usage_metadata field and applying the supplied provider price cards.
func FromLangChainMessage(message Object, options Object, priceCards []any, discountPolicies []any) Object {
	options["adapter"] = "langchain.chat_message"
	return FromResponse(message, options, priceCards, discountPolicies)
}

// FromVercelAISDKResult prices a Vercel AI SDK generateText-like result by
// reading usage or totalUsage and applying the supplied provider price cards.
func FromVercelAISDKResult(result Object, options Object, priceCards []any, discountPolicies []any) Object {
	options["adapter"] = "vercel_ai_sdk.generate_text"
	return FromResponse(result, options, priceCards, discountPolicies)
}

// FromLlamaIndexTokenCounter prices a LlamaIndex TokenCountingHandler-like
// object by reading its LLM token counters and applying provider price cards.
func FromLlamaIndexTokenCounter(counter Object, options Object, priceCards []any, discountPolicies []any) Object {
	options["adapter"] = "llamaindex.token_counter"
	return FromResponse(counter, options, priceCards, discountPolicies)
}

// FromHaystackGeneratorResult prices a Haystack OpenAI generator result by
// reading reply/meta usage metadata and applying provider price cards.
func FromHaystackGeneratorResult(result Object, options Object, priceCards []any, discountPolicies []any) Object {
	options["adapter"] = "haystack.generator_result"
	return FromResponse(result, options, priceCards, discountPolicies)
}

// FromLiteLLMResponse prices a LiteLLM proxy or SDK response by reading
// OpenAI-compatible usage and comparing hidden response_cost metadata when present.
func FromLiteLLMResponse(response Object, options Object, priceCards []any, discountPolicies []any) Object {
	hidden := asObject(response["_hidden_params"])
	if len(hidden) == 0 {
		hidden = asObject(response["hidden_params"])
	}
	if _, exists := options["provider_reported_cost"]; !exists {
		if responseCost, ok := hidden["response_cost"]; ok {
			options["provider_reported_cost"] = responseCost
			if asString(options["provider_reported_cost_mode"]) == "" {
				options["provider_reported_cost_mode"] = "compare"
			}
		}
	}
	options["adapter"] = "litellm.proxy_response"
	return FromResponse(response, options, priceCards, discountPolicies)
}

// FromAG2UsageSummary prices an AG2 usage summary returned from get_actual_usage,
// get_total_usage, or gather_usage_summary.
func FromAG2UsageSummary(summary Object, options Object, priceCards []any, discountPolicies []any) Object {
	usageSummary, _ := ag2UsageSummaryPayload(summary, options)
	_, modelUsage := ag2ModelUsage(usageSummary, asString(options["model"]))
	if _, exists := options["provider_reported_cost"]; !exists {
		reportedCost, hasCost := modelUsage["cost"]
		if !hasCost {
			reportedCost, hasCost = usageSummary["total_cost"]
		}
		if hasCost {
			options["provider_reported_cost"] = reportedCost
			if asString(options["provider_reported_cost_mode"]) == "" {
				options["provider_reported_cost_mode"] = "compare"
			}
		}
	}
	options["adapter"] = "ag2.usage_summary"
	return FromResponse(summary, options, priceCards, discountPolicies)
}
