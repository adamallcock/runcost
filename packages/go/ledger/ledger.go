package ledger

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"math/big"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

//go:embed data/default-source-cache.json
var defaultSourceCacheJSON []byte

// DefaultPriceSourcePriority is the recommended source priority for the bundled catalog.
var DefaultPriceSourcePriority = []string{"llm-prices", "models.dev", "litellm", "openrouter"}

var componentOrder = func() map[string]int {
	orders := map[string]int{}
	for index, name := range componentOrderNames {
		orders[name] = index
	}
	return orders
}()

var toolOrFeatureComponents = map[string]bool{
	"web_search_units":               true,
	"file_search_units":              true,
	"code_interpreter_session_units": true,
	"code_interpreter_call_units":    true,
	"computer_use_action_units":      true,
	"tool_call_units":                true,
	"tool_execution_seconds":         true,
	"rerank_search_units":            true,
	"image_generation_units":         true,
	"video_generation_units":         true,
	"audio_generation_units":         true,
	"audio_generation_characters":    true,
	"transcription_seconds":          true,
	"endpoint_runtime_seconds":       true,
	"storage_gb_days":                true,
}

// Object is the prototype map-backed representation for canonical ledgers,
// price cards, discount policies, provider responses, and adapter inputs.
type Object = map[string]any

// ModelIdentity identifies the requested, returned, and billable model names
// on a canonical usage ledger.
type ModelIdentity struct {
	Requested       string
	Returned        string
	Billed          string
	AliasResolution string
}

// Object converts the model identity to the canonical schema-shaped object.
func (model ModelIdentity) Object() Object {
	result := Object{"requested": model.Requested}
	if model.Returned != "" {
		result["returned"] = model.Returned
	}
	if model.Billed != "" {
		result["billed"] = model.Billed
	}
	if model.AliasResolution != "" {
		result["alias_resolution"] = model.AliasResolution
	}
	return result
}

// ToolMetadata describes a tool or feature usage component's billing source.
type ToolMetadata struct {
	Provider      string
	Name          string
	BillingSource string
}

// Object converts tool metadata to the canonical schema-shaped object.
func (tool ToolMetadata) Object() Object {
	result := Object{}
	if tool.Provider != "" {
		result["provider"] = tool.Provider
	}
	if tool.Name != "" {
		result["name"] = tool.Name
	}
	if tool.BillingSource != "" {
		result["billing_source"] = tool.BillingSource
	}
	return result
}

// UsageComponent is a typed Go representation of a canonical usage component.
type UsageComponent struct {
	Name       string
	Quantity   string
	Unit       string
	Tool       *ToolMetadata
	SourcePath string
	Metadata   Object
}

// Object converts the usage component to the canonical schema-shaped object.
func (component UsageComponent) Object() Object {
	result := Object{
		"name":     component.Name,
		"quantity": component.Quantity,
		"unit":     component.Unit,
	}
	if component.Tool != nil {
		result["tool"] = component.Tool.Object()
	}
	if component.SourcePath != "" {
		result["source_path"] = component.SourcePath
	}
	if component.Metadata != nil {
		result["metadata"] = component.Metadata
	}
	return result
}

// UsageLedger is a typed Go representation of the canonical normalized usage
// ledger contract.
type UsageLedger struct {
	SchemaVersion string
	Provider      string
	Surface       string
	Model         ModelIdentity
	Context       Object
	Components    []UsageComponent
	RawUsage      Object
	Metadata      Object
}

// Object converts the usage ledger to the canonical schema-shaped object.
func (usage UsageLedger) Object() Object {
	result := Object{
		"schema_version": usage.SchemaVersion,
		"provider":       usage.Provider,
		"surface":        usage.Surface,
		"model":          usage.Model.Object(),
		"components":     usageComponentsToAny(usage.Components),
	}
	if usage.Context != nil {
		result["context"] = usage.Context
	}
	if usage.RawUsage != nil {
		result["raw_usage"] = usage.RawUsage
	}
	if usage.Metadata != nil {
		result["metadata"] = usage.Metadata
	}
	return result
}

// Price is a typed Go representation of a component price.
type Price struct {
	Amount   string
	Currency string
	Per      string
}

// Object converts the price to the canonical schema-shaped object.
func (price Price) Object() Object {
	return Object{
		"amount":   price.Amount,
		"currency": price.Currency,
		"per":      price.Per,
	}
}

// PriceConditions limits a price component to a context such as a long-context
// token range.
type PriceConditions struct {
	MinTotalInputTokens string
	MaxTotalInputTokens string
}

// Object converts price conditions to the canonical schema-shaped object.
func (conditions PriceConditions) Object() Object {
	result := Object{}
	if conditions.MinTotalInputTokens != "" {
		result["min_total_input_tokens"] = conditions.MinTotalInputTokens
	}
	if conditions.MaxTotalInputTokens != "" {
		result["max_total_input_tokens"] = conditions.MaxTotalInputTokens
	}
	return result
}

// PriceComponent is a typed Go representation of a canonical price component.
type PriceComponent struct {
	UsageComponent   string
	Unit             string
	Price            Price
	DiscountEligible *bool
	Conditions       *PriceConditions
	Notes            string
}

// Object converts the price component to the canonical schema-shaped object.
func (component PriceComponent) Object() Object {
	result := Object{
		"usage_component": component.UsageComponent,
		"unit":            component.Unit,
		"price":           component.Price.Object(),
	}
	if component.DiscountEligible != nil {
		result["discount_eligible"] = *component.DiscountEligible
	}
	if component.Conditions != nil {
		result["conditions"] = component.Conditions.Object()
	}
	if component.Notes != "" {
		result["notes"] = component.Notes
	}
	return result
}

// Source identifies where a canonical price card came from.
type Source struct {
	Name        string
	URL         string
	RetrievedAt string
	Version     string
	License     string
}

// Object converts the source metadata to the canonical schema-shaped object.
func (source Source) Object() Object {
	result := Object{"name": source.Name}
	if source.URL != "" {
		result["url"] = source.URL
	}
	if source.RetrievedAt != "" {
		result["retrieved_at"] = source.RetrievedAt
	}
	if source.Version != "" {
		result["version"] = source.Version
	}
	if source.License != "" {
		result["license"] = source.License
	}
	return result
}

// EffectiveRange describes when a price card or discount policy applies.
type EffectiveRange struct {
	From string
	To   string
}

// Object converts the effective range to the canonical schema-shaped object.
func (effective EffectiveRange) Object() Object {
	result := Object{}
	if effective.From != "" {
		result["from"] = effective.From
	}
	if effective.To != "" {
		result["to"] = effective.To
	}
	return result
}

// PriceCard is a typed Go representation of a canonical price card.
type PriceCard struct {
	SchemaVersion string
	ID            string
	Provider      string
	Surface       string
	Model         string
	Aliases       []string
	ServiceTier   string
	Region        string
	Effective     *EffectiveRange
	Components    []PriceComponent
	Source        Source
	Metadata      Object
}

// Object converts the price card to the canonical schema-shaped object.
func (card PriceCard) Object() Object {
	result := Object{
		"schema_version": card.SchemaVersion,
		"id":             card.ID,
		"provider":       card.Provider,
		"model":          card.Model,
		"components":     priceComponentsToAny(card.Components),
		"source":         card.Source.Object(),
	}
	if card.Surface != "" {
		result["surface"] = card.Surface
	}
	if len(card.Aliases) > 0 {
		result["aliases"] = stringsToAny(card.Aliases)
	}
	if card.ServiceTier != "" {
		result["service_tier"] = card.ServiceTier
	}
	if card.Region != "" {
		result["region"] = card.Region
	}
	if card.Effective != nil {
		result["effective"] = card.Effective.Object()
	}
	if card.Metadata != nil {
		result["metadata"] = card.Metadata
	}
	return result
}

// DiscountMatch describes when a discount policy applies.
type DiscountMatch struct {
	Provider          string
	Surface           string
	Model             string
	ServiceTier       string
	Region            string
	Components        []string
	ExcludeComponents []string
	Tags              map[string]string
}

// Object converts the discount match to the canonical schema-shaped object.
func (match DiscountMatch) Object() Object {
	result := Object{}
	if match.Provider != "" {
		result["provider"] = match.Provider
	}
	if match.Surface != "" {
		result["surface"] = match.Surface
	}
	if match.Model != "" {
		result["model"] = match.Model
	}
	if match.ServiceTier != "" {
		result["service_tier"] = match.ServiceTier
	}
	if match.Region != "" {
		result["region"] = match.Region
	}
	if len(match.Components) > 0 {
		result["components"] = stringsToAny(match.Components)
	}
	if len(match.ExcludeComponents) > 0 {
		result["exclude_components"] = stringsToAny(match.ExcludeComponents)
	}
	if len(match.Tags) > 0 {
		tags := Object{}
		for key, value := range match.Tags {
			tags[key] = value
		}
		result["tags"] = tags
	}
	return result
}

// DiscountAdjustment describes the discount or markup applied by a policy.
type DiscountAdjustment struct {
	Type  string
	Value string
}

// Object converts the discount adjustment to the canonical schema-shaped
// object.
func (adjustment DiscountAdjustment) Object() Object {
	return Object{
		"type":  adjustment.Type,
		"value": adjustment.Value,
	}
}

// DiscountPolicy is a typed Go representation of a canonical discount policy.
type DiscountPolicy struct {
	SchemaVersion string
	ID            string
	Description   string
	Match         DiscountMatch
	Effective     *EffectiveRange
	Adjustment    DiscountAdjustment
	Precedence    *int
	Metadata      Object
}

// Object converts the discount policy to the canonical schema-shaped object.
func (policy DiscountPolicy) Object() Object {
	result := Object{
		"schema_version": policy.SchemaVersion,
		"id":             policy.ID,
		"adjustment":     policy.Adjustment.Object(),
	}
	if policy.Description != "" {
		result["description"] = policy.Description
	}
	match := policy.Match.Object()
	if len(match) > 0 {
		result["match"] = match
	}
	if policy.Effective != nil {
		result["effective"] = policy.Effective.Object()
	}
	if policy.Precedence != nil {
		result["precedence"] = *policy.Precedence
	}
	if policy.Metadata != nil {
		result["metadata"] = policy.Metadata
	}
	return result
}

// CostOptions is a typed Go wrapper for common calculator options. Raw can be
// used for temporary experimental options that are already understood by the
// map-backed core.
type CostOptions struct {
	Mode                     string
	PriceSourcePriority      []string
	ProviderReportedCost     string
	ProviderReportedCostMode string
	StaleAfterDays           *int
	DebugTrace               bool
	Raw                      Object
}

// Object converts calculator options to the map-backed option object consumed
// by the core.
func (options CostOptions) Object() Object {
	result := Object{}
	for key, value := range options.Raw {
		result[key] = value
	}
	if options.Mode != "" {
		result["mode"] = options.Mode
	}
	if len(options.PriceSourcePriority) > 0 {
		result["price_source_priority"] = stringsToAny(options.PriceSourcePriority)
	}
	if options.ProviderReportedCost != "" {
		result["provider_reported_cost"] = options.ProviderReportedCost
	}
	if options.ProviderReportedCostMode != "" {
		result["provider_reported_cost_mode"] = options.ProviderReportedCostMode
	}
	if options.StaleAfterDays != nil {
		result["stale_after_days"] = *options.StaleAfterDays
	}
	if options.DebugTrace {
		result["debug_trace"] = true
	}
	return result
}

// CalculateCostTyped returns a componentized cost ledger for typed Go usage,
// price-card, and discount-policy structs.
func CalculateCostTyped(usageLedger UsageLedger, priceCards []PriceCard, discountPolicies []DiscountPolicy) Object {
	return CalculateCostTypedWithMode(usageLedger, priceCards, discountPolicies, "compatibility")
}

// CalculateCostTypedWithMode returns a componentized cost ledger for typed Go
// inputs using either "compatibility" or "strict" mode.
func CalculateCostTypedWithMode(usageLedger UsageLedger, priceCards []PriceCard, discountPolicies []DiscountPolicy, mode string) Object {
	return CalculateCostTypedWithOptions(usageLedger, priceCards, discountPolicies, CostOptions{Mode: mode})
}

// CalculateCostTypedWithOptions returns a componentized cost ledger for typed Go
// inputs and typed calculator options.
func CalculateCostTypedWithOptions(usageLedger UsageLedger, priceCards []PriceCard, discountPolicies []DiscountPolicy, options CostOptions) Object {
	return CalculateCostWithOptions(usageLedger.Object(), priceCardsToAny(priceCards), discountPoliciesToAny(discountPolicies), options.Object())
}

func stringsToAny(values []string) []any {
	result := []any{}
	for _, value := range values {
		result = append(result, value)
	}
	return result
}

func usageComponentsToAny(components []UsageComponent) []any {
	result := []any{}
	for _, component := range components {
		result = append(result, component.Object())
	}
	return result
}

func priceComponentsToAny(components []PriceComponent) []any {
	result := []any{}
	for _, component := range components {
		result = append(result, component.Object())
	}
	return result
}

func priceCardsToAny(cards []PriceCard) []any {
	result := []any{}
	for _, card := range cards {
		result = append(result, card.Object())
	}
	return result
}

func discountPoliciesToAny(policies []DiscountPolicy) []any {
	result := []any{}
	for _, policy := range policies {
		result = append(result, policy.Object())
	}
	return result
}

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

func cardModelSurfaceMatches(usageLedger Object, card Object) bool {
	model := billedModel(usageLedger)
	modelMatches := asString(card["model"]) == model || containsString(asSlice(card["aliases"]), model)
	surface := asString(card["surface"])
	surfaceMatches := surface == "" || surface == asString(usageLedger["surface"])
	return modelMatches && surfaceMatches
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
		leftSource := asString(asObject(scored[left].card["source"])["name"])
		rightSource := asString(asObject(scored[right].card["source"])["name"])
		if leftSource != rightSource {
			return leftSource < rightSource
		}
		leftID := asString(scored[left].card["id"])
		rightID := asString(scored[right].card["id"])
		if leftID != rightID {
			return leftID < rightID
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

func warningIdentityMetadata(usageLedger Object) Object {
	return Object{
		"provider": asString(usageLedger["provider"]),
		"surface":  asString(usageLedger["surface"]),
		"model":    billedModel(usageLedger),
	}
}

func aliasInferredWarning(requestedModel string, billedModelValue string) Object {
	return Object{
		"code":    "alias_inferred",
		"message": fmt.Sprintf("Resolved model alias %s to billed model %s.", requestedModel, billedModelValue),
		"metadata": Object{
			"requested_model": requestedModel,
			"billed_model":    billedModelValue,
		},
	}
}

func unpricedComponentMetadata(usageLedger Object, component Object) Object {
	return Object{
		"component": asString(component["name"]),
		"unit":      asString(component["unit"]),
		"model":     billedModel(usageLedger),
	}
}

func isToolOrFeatureComponent(componentName string) bool {
	return toolOrFeatureComponents[componentName]
}

func unpricedComponentWarning(usageLedger Object, component Object) Object {
	componentName := asString(component["name"])
	if isToolOrFeatureComponent(componentName) {
		return Object{
			"code": "tool_component_unpriced",
			"message": fmt.Sprintf(
				"No price found for tool or feature component %s on model %s.",
				componentName,
				billedModel(usageLedger),
			),
			"metadata": unpricedComponentMetadata(usageLedger, component),
		}
	}
	return Object{
		"code":     "component_unpriced",
		"message":  fmt.Sprintf("No price found for %s (%s).", componentName, asString(component["unit"])),
		"metadata": unpricedComponentMetadata(usageLedger, component),
	}
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
	totalInput := decimal(totalInputTokens(usageLedger))
	return Object{
		"code":    "long_context_rule_missing",
		"message": fmt.Sprintf("No long-context pricing rule matched %s at %s input tokens.", asString(component["name"]), totalInput),
		"metadata": Object{
			"component":          asString(component["name"]),
			"unit":               asString(component["unit"]),
			"total_input_tokens": totalInput,
		},
	}, true
}

func sourceCapabilityWarning(matchingCards []Object, component Object) (Object, bool) {
	componentName := asString(component["name"])
	for _, card := range matchingCards {
		metadata := asObject(card["metadata"])
		capabilities := asObject(metadata["source_capabilities"])
		if len(capabilities) == 0 {
			continue
		}
		unsupported := asSlice(capabilities["unsupported_components"])
		if unsupported == nil {
			unsupported = asSlice(capabilities["unsupportedComponents"])
		}
		for _, rawUnsupported := range unsupported {
			if asString(rawUnsupported) == componentName {
				source := asObject(card["source"])
				sourceName := asString(source["name"])
				if sourceName == "" {
					sourceName = asString(card["id"])
				}
				return Object{
					"code":    "source_capability_unsupported",
					"message": fmt.Sprintf("Price source %s explicitly does not price %s.", sourceName, componentName),
					"metadata": Object{
						"component":     componentName,
						"price_card_id": card["id"],
						"source":        asString(source["name"]),
					},
				}, true
			}
		}
	}
	return nil, false
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

func hasPriceCardForModelSurface(usageLedger Object, priceCards []any) bool {
	for _, rawCard := range priceCards {
		card := asObject(rawCard)
		if cardModelSurfaceMatches(usageLedger, card) {
			return true
		}
	}
	return false
}

func unknownProviderWarning(usageLedger Object) Object {
	provider := asString(usageLedger["provider"])
	return Object{
		"code":     "unknown_provider",
		"message":  fmt.Sprintf("No price card found for provider %s.", provider),
		"metadata": warningIdentityMetadata(usageLedger),
	}
}

func unknownModelWarning(usageLedger Object) Object {
	model := billedModel(usageLedger)
	return Object{
		"code":     "unknown_model",
		"message":  fmt.Sprintf("No price card found for %s.", model),
		"metadata": warningIdentityMetadata(usageLedger),
	}
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
				"metadata": Object{
					"model":        billedModel(usageLedger),
					"service_tier": serviceTier,
				},
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
				"metadata": Object{
					"model":     billedModel(usageLedger),
					"priced_at": pricedAt,
				},
			}
		}
	}
	return Object{
		"code":     "price_not_found",
		"message":  fmt.Sprintf("No price card matched provider, surface, model, and context for %s.", billedModel(usageLedger)),
		"metadata": warningIdentityMetadata(usageLedger),
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

func discountNotAppliedWarnings(policies []any, appliedDiscounts []any) []any {
	appliedPolicyIDs := map[string]bool{}
	for _, rawDiscount := range appliedDiscounts {
		discount := asObject(rawDiscount)
		appliedPolicyIDs[asString(discount["policy_id"])] = true
	}
	warnings := []any{}
	for _, rawPolicy := range policies {
		policy := asObject(rawPolicy)
		metadata := asObject(policy["metadata"])
		if value, ok := metadata["warn_if_unapplied"].(bool); !ok || !value {
			continue
		}
		policyID := asString(policy["id"])
		if appliedPolicyIDs[policyID] {
			continue
		}
		warnings = append(warnings, Object{
			"code":    "discount_not_applied",
			"message": fmt.Sprintf("Discount policy %s did not apply to any priced component.", policyID),
			"metadata": Object{
				"policy_id": policyID,
			},
		})
	}
	return warnings
}

func usageMetadataFieldWarnings(usageLedger Object) []any {
	metadata := asObject(usageLedger["metadata"])
	warnings := []any{}
	for _, rawField := range asSlice(metadata["ignored_usage_fields"]) {
		field := asString(rawField)
		warnings = append(warnings, Object{
			"code":    "usage_field_ignored",
			"message": fmt.Sprintf("Usage field %s was not mapped to a cost component.", field),
			"path":    field,
			"metadata": Object{
				"field": field,
			},
		})
	}
	for _, rawField := range asSlice(metadata["inclusive_usage_fields"]) {
		field := asString(rawField)
		warnings = append(warnings, Object{
			"code":    "inclusive_usage_ambiguous",
			"message": fmt.Sprintf("Usage field %s appears inclusive; RunCost priced component fields instead.", field),
			"path":    field,
			"metadata": Object{
				"field": field,
			},
		})
	}
	return warnings
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
		"metadata": Object{
			"source":         sourceName,
			"age_days":       ageDays,
			"threshold_days": threshold,
			"retrieved_at":   asString(asObject(card["source"])["retrieved_at"]),
			"priced_at":      datePart(usageContext(usageLedger)["priced_at"]),
		},
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
		"metadata": Object{
			"provider_reported_cost": providerTotal,
			"calculated_total":       total,
		},
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
		"metadata": Object{
			"provider_reported_cost": providerTotal,
			"calculated_total":       total,
		},
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
		"metadata": Object{
			"component":                asString(component["name"]),
			"selected_price_card_id":   chosen,
			"candidate_price_card_ids": matchPriceCardIDs(matches),
		},
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
	warnings := usageMetadataFieldWarnings(usageLedger)
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
	modelSurfaceCardExists := hasPriceCardForModelSurface(usageLedger, priceCards)
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
	warnedUnknownProvider := false
	warnedNoMatchingCard := false
	warnedAliasInferred := false
	warnedStaleCards := map[string]bool{}

	for _, rawComponent := range asSlice(usageLedger["components"]) {
		component := asObject(rawComponent)
		if !hasModelCard {
			if modelSurfaceCardExists {
				if !warnedUnknownProvider {
					warnings = append(warnings, unknownProviderWarning(usageLedger))
					warnedUnknownProvider = true
				}
			} else if !warnedUnknownModel {
				warnings = append(warnings, unknownModelWarning(usageLedger))
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
			if warning, ok := sourceCapabilityWarning(candidateCards, component); ok {
				warnings = append(warnings, warning)
			} else if warning, ok := longContextRuleMissingWarning(usageLedger, candidates, component); ok {
				warnings = append(warnings, warning)
			} else {
				warnings = append(warnings, unpricedComponentWarning(usageLedger, component))
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
				if !warnedAliasInferred {
					warnings = append(warnings, aliasInferredWarning(previousBilledModel, resolvedBilledModel))
					warnedAliasInferred = true
				}
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
	warnings = append(warnings, discountNotAppliedWarnings(discountPolicies, appliedDiscounts)...)
	components = orderedCostComponents(components)
	priceSources = orderedPriceSources(priceSources)
	appliedDiscounts = orderedAppliedDiscounts(appliedDiscounts)
	warnings = orderedWarnings(warnings)
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

func componentRank(name string) int {
	if rank, ok := componentOrder[name]; ok {
		return rank
	}
	return len(componentOrder)
}

func orderedCostComponents(components []any) []any {
	ordered := append([]any{}, components...)
	sort.SliceStable(ordered, func(left int, right int) bool {
		leftComponent := asObject(ordered[left])
		rightComponent := asObject(ordered[right])
		leftRank := componentRank(asString(leftComponent["name"]))
		rightRank := componentRank(asString(rightComponent["name"]))
		if leftRank != rightRank {
			return leftRank < rightRank
		}
		leftKey := strings.Join([]string{
			asString(leftComponent["name"]),
			asString(leftComponent["unit"]),
			asString(leftComponent["unit_price"]),
			asString(leftComponent["price_card_id"]),
			numberString(leftComponent["quantity"]),
			numberString(leftComponent["cost"]),
		}, "|")
		rightKey := strings.Join([]string{
			asString(rightComponent["name"]),
			asString(rightComponent["unit"]),
			asString(rightComponent["unit_price"]),
			asString(rightComponent["price_card_id"]),
			numberString(rightComponent["quantity"]),
			numberString(rightComponent["cost"]),
		}, "|")
		return leftKey < rightKey
	})
	return ordered
}

func orderedPriceSources(sources []any) []any {
	ordered := append([]any{}, sources...)
	sort.SliceStable(ordered, func(left int, right int) bool {
		return sourceKey(asObject(ordered[left])) < sourceKey(asObject(ordered[right]))
	})
	return ordered
}

func orderedAppliedDiscounts(discounts []any) []any {
	ordered := append([]any{}, discounts...)
	sort.SliceStable(ordered, func(left int, right int) bool {
		leftDiscount := asObject(ordered[left])
		rightDiscount := asObject(ordered[right])
		leftKey := strings.Join([]string{
			asString(leftDiscount["component"]),
			asString(leftDiscount["policy_id"]),
			numberString(leftDiscount["amount"]),
		}, "|")
		rightKey := strings.Join([]string{
			asString(rightDiscount["component"]),
			asString(rightDiscount["policy_id"]),
			numberString(rightDiscount["amount"]),
		}, "|")
		return leftKey < rightKey
	})
	return ordered
}

func orderedWarnings(warnings []any) []any {
	ordered := append([]any{}, warnings...)
	sort.SliceStable(ordered, func(left int, right int) bool {
		leftWarning := asObject(ordered[left])
		rightWarning := asObject(ordered[right])
		leftMetadata, _ := json.Marshal(leftWarning["metadata"])
		rightMetadata, _ := json.Marshal(rightWarning["metadata"])
		leftKey := strings.Join([]string{
			asString(leftWarning["code"]),
			asString(leftWarning["path"]),
			asString(leftWarning["message"]),
			string(leftMetadata),
		}, "|")
		rightKey := strings.Join([]string{
			asString(rightWarning["code"]),
			asString(rightWarning["path"]),
			asString(rightWarning["message"]),
			string(rightMetadata),
		}, "|")
		return leftKey < rightKey
	})
	return ordered
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
	components = orderedCostComponents(components)
	priceSources = orderedPriceSources(priceSources)
	appliedDiscounts = orderedAppliedDiscounts(appliedDiscounts)
	warnings = orderedWarnings(warnings)
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

func openAICompatibleChatPayload(response Object) Object {
	chunks := asSlice(response["chunks"])
	if len(chunks) == 0 {
		chunks = asSlice(response["stream"])
	}
	if len(chunks) == 0 {
		return response
	}
	for index := len(chunks) - 1; index >= 0; index-- {
		chunk := asObject(chunks[index])
		if _, ok := chunk["usage"]; ok {
			usage := asObject(chunk["usage"])
			if len(usage) == 0 {
				continue
			}
			payload := Object{}
			for key, value := range chunk {
				payload[key] = value
			}
			if asString(payload["model"]) == "" && asString(response["model"]) != "" {
				payload["model"] = response["model"]
			}
			return payload
		}
	}
	return response
}

// ExtractUsageLedger normalizes a raw provider response into the canonical usage
// ledger shape for supported surfaces.
//
// Supported prototype surfaces include OpenAI Responses, OpenAI-compatible chat
// completions, Anthropic Messages, Cohere Chat, Gemini generateContent, AWS
// Bedrock Converse, and AWS Bedrock InvokeModel.
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
	case "vercel_ai_sdk.stream_text":
		return extractVercelAISDKUsage(response, options)
	case "llamaindex.token_counter":
		return extractLlamaIndexTokenCounterUsage(response, options)
	case "haystack.generator_result":
		return extractHaystackGeneratorUsage(response, options)
	case "litellm.proxy_response":
		return extractLiteLLMProxyResponseUsage(response, options)
	case "ag2.usage_summary":
		return extractAG2UsageSummaryUsage(response, options)
	case "openai_agents.usage":
		return extractOpenAIAgentsUsage(response, options)
	case "langsmith.run_usage":
		return extractLangSmithRunUsage(response, options)
	case "semantic_kernel.telemetry":
		return extractSemanticKernelTelemetryUsage(response, options)
	case "openrouter.sdk_response":
		return extractOpenRouterSDKResponseUsage(response, options)
	}

	surface := asString(options["surface"])
	switch surface {
	case "openai.responses", "xai.responses":
		return extractOpenAIResponsesUsage(response, options)
	case "openai.embeddings":
		return extractOpenAIEmbeddingsUsage(response, options)
	case "openai.audio_transcriptions":
		return extractOpenAIAudioTranscriptionUsage(response, options)
	case "openai.images":
		return extractOpenAIImagesUsage(response, options)
	case "openai.usage.images":
		return extractOpenAIUsageImagesUsage(response, options)
	case "openai.usage.completions":
		return extractOpenAIUsageCompletionsUsage(response, options)
	case "openai.usage.audio_speeches":
		return extractOpenAIUsageAudioSpeechesUsage(response, options)
	case "openai.usage.audio_transcriptions":
		return extractOpenAIUsageAudioTranscriptionsUsage(response, options)
	case "openai.usage.embeddings":
		return extractOpenAIUsageEmbeddingsUsage(response, options)
	case "openai.vector_stores":
		return extractOpenAIVectorStoreStorageUsage(response, options)
	case "openai.usage.code_interpreter_sessions":
		return extractOpenAIUsageCodeInterpreterSessionsUsage(response, options)
	case "openai.chat_completions":
		return extractOpenAIChatCompletionsUsage(response, options)
	case "anthropic.messages":
		return extractAnthropicMessagesUsage(response, options)
	case "google.gemini.generate_content", "vertex.gemini.generate_content":
		return extractGeminiGenerateContentUsage(response, options)
	case "aws.bedrock.converse":
		return extractBedrockConverseUsage(response, options)
	case "aws.bedrock.invoke_model":
		return extractBedrockInvokeModelUsage(response, options)
	case "cohere.chat":
		return extractCohereChatUsage(response, options)
	case "cohere.rerank":
		return extractCohereRerankUsage(response, options)
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
				"metadata": Object{
					"provider": provider,
					"surface":  surface,
					"model":    model,
				},
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
	functionCallCount := 0
	for _, rawItem := range asSlice(response["output"]) {
		item := asObject(rawItem)
		switch asString(item["type"]) {
		case "web_search_call":
			toolComponents = append(toolComponents, positiveComponent("web_search_units", "1", "search", "$.output[*].type"))
		case "file_search_call":
			toolComponents = append(toolComponents, positiveComponent("file_search_units", "1", "call", "$.output[*].type"))
		case "code_interpreter_call":
			toolComponents = append(toolComponents, positiveComponent("code_interpreter_call_units", "1", "call", "$.output[*].type"))
		case "computer_call":
			actionCount := len(asSlice(item["actions"]))
			if actionCount == 0 {
				actionCount = 1
			}
			toolComponents = append(toolComponents, positiveComponent("computer_use_action_units", strconv.Itoa(actionCount), "call", "$.output[*].actions[*]"))
		case "function_call":
			functionCallCount++
		}
	}
	toolComponents = append(toolComponents, positiveComponent("tool_call_units", strconv.Itoa(functionCallCount), "call", "$.output[*].type"))
	provider := asString(options["provider"])
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.responses"
	}
	if provider == "" {
		if surface == "xai.responses" {
			provider = "xai"
		} else {
			provider = "openai"
		}
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
	return baseUsageLedger(provider, surface, requestedModel, asString(response["model"]), compactComponents(components), usage)
}

func extractOpenAIEmbeddingsUsage(response Object, options Object) Object {
	usage := asObject(response["usage"])
	tokens := getNumber(usage, "prompt_tokens")
	sourcePath := "$.usage.prompt_tokens"
	if _, ok := usage["prompt_tokens"]; !ok {
		tokens = getNumber(usage, "total_tokens")
		sourcePath = "$.usage.total_tokens"
	}
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.embeddings"
	}
	requestedModel := asString(options["model"])
	if requestedModel == "" {
		requestedModel = asString(response["model"])
	}

	return baseUsageLedger(provider, surface, requestedModel, asString(response["model"]), compactComponents([]any{
		positiveComponent("embedding_tokens", tokens, "token", sourcePath),
	}), usage)
}

func extractOpenAIAudioTranscriptionUsage(response Object, options Object) Object {
	usage := asObject(response["usage"])
	components := []any{}
	if asString(usage["type"]) == "duration" || usage["seconds"] != nil {
		components = append(components, positiveComponent("transcription_seconds", getNumber(usage, "seconds"), "second", "$.usage.seconds"))
	} else if len(usage) > 0 {
		inputDetails := asObject(usage["input_token_details"])
		audioTokens := getNumber(inputDetails, "audio_tokens")
		inputTokens := getNumber(usage, "input_tokens")
		textTokens := getNumber(inputDetails, "text_tokens")
		if _, ok := inputDetails["text_tokens"]; !ok {
			textTokens = subtract(inputTokens, audioTokens)
		}
		components = append(components,
			positiveComponent("input_uncached_tokens", textTokens, "token", "$.usage.input_token_details.text_tokens"),
			positiveComponent("input_audio_tokens", audioTokens, "token", "$.usage.input_token_details.audio_tokens"),
			positiveComponent("output_text_tokens", getNumber(usage, "output_tokens"), "token", "$.usage.output_tokens"),
		)
	} else if response["duration"] != nil {
		components = append(components, positiveComponent("transcription_seconds", response["duration"], "second", "$.duration"))
		usage = Object{"duration": response["duration"]}
	}
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.audio_transcriptions"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}
	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents(components), usage)
}

func extractOpenAIImagesUsage(response Object, options Object) Object {
	usage := asObject(response["usage"])
	components := []any{}
	if len(usage) > 0 {
		inputDetails := asObject(usage["input_tokens_details"])
		inputImageTokens := getNumber(inputDetails, "image_tokens")
		inputTokens := getNumber(usage, "input_tokens")
		inputTextTokens := getNumber(inputDetails, "text_tokens")
		if _, ok := inputDetails["text_tokens"]; !ok {
			inputTextTokens = subtract(inputTokens, inputImageTokens)
		}
		outputDetails := asObject(usage["output_tokens_details"])
		outputImageTokens := getNumber(outputDetails, "image_tokens")
		if _, ok := outputDetails["image_tokens"]; !ok {
			outputImageTokens = getNumber(usage, "output_tokens")
		}
		components = append(components,
			positiveComponent("input_uncached_tokens", inputTextTokens, "token", "$.usage.input_tokens_details.text_tokens"),
			positiveComponent("input_image_tokens", inputImageTokens, "token", "$.usage.input_tokens_details.image_tokens"),
			positiveComponent("output_image_tokens", outputImageTokens, "token", "$.usage.output_tokens"),
		)
	} else {
		images := asSlice(response["data"])
		components = append(components, positiveComponent("image_generation_units", strconv.Itoa(len(images)), "image", "$.data"))
		usage = Object{"image_count": len(images)}
	}
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.images"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}
	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents(components), usage)
}

func openAIUsageImagesCount(response Object) string {
	if asString(response["object"]) == "organization.usage.images.result" {
		return numberString(response["images"])
	}
	total := "0"
	for _, bucketValue := range asSlice(response["data"]) {
		bucket := asObject(bucketValue)
		for _, resultValue := range asSlice(bucket["results"]) {
			result := asObject(resultValue)
			total = add(total, getNumber(result, "images"))
		}
	}
	if rat(total).Sign() == 0 && response["images"] != nil {
		total = add(total, response["images"])
	}
	return total
}

func openAIUsageFirstResultValue(response Object, key string) any {
	if response[key] != nil {
		return response[key]
	}
	for _, bucketValue := range asSlice(response["data"]) {
		bucket := asObject(bucketValue)
		for _, resultValue := range asSlice(bucket["results"]) {
			result := asObject(resultValue)
			if result[key] != nil {
				return result[key]
			}
		}
	}
	return nil
}

func openAIUsageSumResultValue(response Object, key string) string {
	if response[key] != nil {
		return numberString(response[key])
	}
	total := "0"
	for _, bucketValue := range asSlice(response["data"]) {
		bucket := asObject(bucketValue)
		for _, resultValue := range asSlice(bucket["results"]) {
			result := asObject(resultValue)
			total = add(total, getNumber(result, key))
		}
	}
	return total
}

func extractOpenAIUsageCompletionsUsage(response Object, options Object) Object {
	inputTokens := openAIUsageSumResultValue(response, "input_tokens")
	cachedTokens := openAIUsageSumResultValue(response, "input_cached_tokens")
	uncachedTokens := subtract(inputTokens, cachedTokens)
	if rat(uncachedTokens).Sign() < 0 {
		uncachedTokens = "0"
	}
	outputTokens := openAIUsageSumResultValue(response, "output_tokens")
	inputAudioTokens := openAIUsageSumResultValue(response, "input_audio_tokens")
	outputAudioTokens := openAIUsageSumResultValue(response, "output_audio_tokens")
	numModelRequests := openAIUsageSumResultValue(response, "num_model_requests")
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.usage.completions"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if returnedModel == "" {
		returnedModel = asString(openAIUsageFirstResultValue(response, "model"))
	}
	if returnedModel == "" {
		returnedModel = "completions"
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}
	rawUsage := Object{
		"input_tokens":        inputTokens,
		"input_cached_tokens": cachedTokens,
		"output_tokens":       outputTokens,
		"input_audio_tokens":  inputAudioTokens,
		"output_audio_tokens": outputAudioTokens,
		"num_model_requests":  numModelRequests,
	}
	if value := openAIUsageFirstResultValue(response, "batch"); value != nil {
		rawUsage["batch"] = value
	}
	if value := openAIUsageFirstResultValue(response, "service_tier"); value != nil {
		rawUsage["service_tier"] = value
	}
	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", uncachedTokens, "token", "$..input_tokens"),
		positiveComponent("input_cache_read_tokens", cachedTokens, "token", "$..input_cached_tokens"),
		positiveComponent("input_audio_tokens", inputAudioTokens, "token", "$..input_audio_tokens"),
		positiveComponent("output_text_tokens", outputTokens, "token", "$..output_tokens"),
		positiveComponent("output_audio_tokens", outputAudioTokens, "token", "$..output_audio_tokens"),
	}), rawUsage)
}

func extractOpenAIUsageImagesUsage(response Object, options Object) Object {
	images := openAIUsageImagesCount(response)
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.usage.images"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if returnedModel == "" {
		returnedModel = asString(openAIUsageFirstResultValue(response, "model"))
	}
	if returnedModel == "" {
		returnedModel = "image-generation"
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}
	rawUsage := Object{"images": images}
	if value := openAIUsageFirstResultValue(response, "num_model_requests"); value != nil {
		rawUsage["num_model_requests"] = value
	}
	if value := openAIUsageFirstResultValue(response, "source"); value != nil {
		rawUsage["source"] = value
	}
	if value := openAIUsageFirstResultValue(response, "size"); value != nil {
		rawUsage["size"] = value
	}
	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("image_generation_units", images, "image", "$..images"),
	}), rawUsage)
}

func openAIUsageAudioSpeechCharacters(response Object) string {
	if asString(response["object"]) == "organization.usage.audio_speeches.result" {
		return numberString(response["characters"])
	}
	total := "0"
	for _, bucketValue := range asSlice(response["data"]) {
		bucket := asObject(bucketValue)
		for _, resultValue := range asSlice(bucket["results"]) {
			result := asObject(resultValue)
			total = add(total, getNumber(result, "characters"))
		}
	}
	if rat(total).Sign() == 0 && response["characters"] != nil {
		total = add(total, response["characters"])
	}
	return total
}

func extractOpenAIUsageAudioSpeechesUsage(response Object, options Object) Object {
	characters := openAIUsageAudioSpeechCharacters(response)
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.usage.audio_speeches"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if returnedModel == "" {
		returnedModel = asString(openAIUsageFirstResultValue(response, "model"))
	}
	if returnedModel == "" {
		returnedModel = "audio-speech"
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}
	rawUsage := Object{"characters": characters}
	if value := openAIUsageFirstResultValue(response, "num_model_requests"); value != nil {
		rawUsage["num_model_requests"] = value
	}
	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("audio_generation_characters", characters, "character", "$..characters"),
	}), rawUsage)
}

func openAIUsageAudioTranscriptionSeconds(response Object) string {
	if asString(response["object"]) == "organization.usage.audio_transcriptions.result" {
		return numberString(response["seconds"])
	}
	total := "0"
	for _, bucketValue := range asSlice(response["data"]) {
		bucket := asObject(bucketValue)
		for _, resultValue := range asSlice(bucket["results"]) {
			result := asObject(resultValue)
			total = add(total, getNumber(result, "seconds"))
		}
	}
	if rat(total).Sign() == 0 && response["seconds"] != nil {
		total = add(total, response["seconds"])
	}
	return total
}

func extractOpenAIUsageAudioTranscriptionsUsage(response Object, options Object) Object {
	seconds := openAIUsageAudioTranscriptionSeconds(response)
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.usage.audio_transcriptions"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if returnedModel == "" {
		returnedModel = asString(openAIUsageFirstResultValue(response, "model"))
	}
	if returnedModel == "" {
		returnedModel = "audio-transcription"
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}
	rawUsage := Object{"seconds": seconds}
	if value := openAIUsageFirstResultValue(response, "num_model_requests"); value != nil {
		rawUsage["num_model_requests"] = value
	}
	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("transcription_seconds", seconds, "second", "$..seconds"),
	}), rawUsage)
}

func openAIUsageEmbeddingTokens(response Object) string {
	if asString(response["object"]) == "organization.usage.embeddings.result" {
		return numberString(response["input_tokens"])
	}
	total := "0"
	for _, bucketValue := range asSlice(response["data"]) {
		bucket := asObject(bucketValue)
		for _, resultValue := range asSlice(bucket["results"]) {
			result := asObject(resultValue)
			total = add(total, getNumber(result, "input_tokens"))
		}
	}
	if rat(total).Sign() == 0 && response["input_tokens"] != nil {
		total = add(total, response["input_tokens"])
	}
	return total
}

func extractOpenAIUsageEmbeddingsUsage(response Object, options Object) Object {
	inputTokens := openAIUsageEmbeddingTokens(response)
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.usage.embeddings"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if returnedModel == "" {
		returnedModel = asString(openAIUsageFirstResultValue(response, "model"))
	}
	if returnedModel == "" {
		returnedModel = "embedding"
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}
	rawUsage := Object{"input_tokens": inputTokens}
	if value := openAIUsageFirstResultValue(response, "num_model_requests"); value != nil {
		rawUsage["num_model_requests"] = value
	}
	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("embedding_tokens", inputTokens, "token", "$..input_tokens"),
	}), rawUsage)
}

func extractOpenAIVectorStoreStorageUsage(response Object, options Object) Object {
	usageBytes := response["usage_bytes"]
	if usageBytes == nil {
		usageBytes = json.Number("0")
	}
	storageDays := options["storage_days"]
	if storageDays == nil {
		storageDays = options["storageDays"]
	}
	if storageDays == nil {
		storageDays = json.Number("0")
	}
	components := []any{}
	if rat(storageDays).Sign() > 0 {
		quantity := multiplyDivide(usageBytes, storageDays, "1000000000")
		components = append(components, positiveComponent("storage_gb_days", quantity, "gb_day", "$.usage_bytes"))
	}
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.vector_stores"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if returnedModel == "" {
		returnedModel = "vector-store-storage"
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}
	usage := Object{
		"usage_bytes":  usageBytes,
		"storage_days": storageDays,
	}
	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents(components), usage)
}

func openAIUsageCodeInterpreterSessionCount(response Object) string {
	if asString(response["object"]) == "organization.usage.code_interpreter_sessions.result" {
		return numberString(response["num_sessions"])
	}
	total := "0"
	for _, bucketValue := range asSlice(response["data"]) {
		bucket := asObject(bucketValue)
		for _, resultValue := range asSlice(bucket["results"]) {
			result := asObject(resultValue)
			total = add(total, getNumber(result, "num_sessions"))
		}
	}
	if rat(total).Sign() == 0 && response["num_sessions"] != nil {
		total = add(total, response["num_sessions"])
	}
	return total
}

func extractOpenAIUsageCodeInterpreterSessionsUsage(response Object, options Object) Object {
	numSessions := openAIUsageCodeInterpreterSessionCount(response)
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.usage.code_interpreter_sessions"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if returnedModel == "" {
		returnedModel = "code-interpreter-session"
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}
	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("code_interpreter_session_units", numSessions, "session", "$..num_sessions"),
	}), Object{"num_sessions": numSessions})
}

func extractOpenAICompatibleChatCompletionsUsage(response Object, options Object) Object {
	response = openAICompatibleChatPayload(response)
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

func bedrockInvokeModelBody(response Object) (Object, string) {
	rawBody, ok := response["body"]
	if !ok {
		return response, "$"
	}
	switch body := rawBody.(type) {
	case map[string]any:
		return body, "$.body"
	case string:
		decoder := json.NewDecoder(strings.NewReader(body))
		decoder.UseNumber()
		var decoded Object
		if err := decoder.Decode(&decoded); err == nil {
			return decoded, "$.body"
		}
	case []byte:
		decoder := json.NewDecoder(strings.NewReader(string(body)))
		decoder.UseNumber()
		var decoded Object
		if err := decoder.Decode(&decoded); err == nil {
			return decoded, "$.body"
		}
	}
	return Object{}, "$.body"
}

func extractBedrockInvokeModelUsage(response Object, options Object) Object {
	body, sourceRoot := bedrockInvokeModelBody(response)
	usage := asObject(body["usage"])
	cacheWrite := getNumber(usage, "cache_creation_input_tokens")
	cacheWrite1h := getNumber(usage, "cache_creation_input_tokens_1h")
	provider := asString(options["provider"])
	if provider == "" {
		provider = "bedrock"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "aws.bedrock.invoke_model"
	}
	returnedModel := asString(response["modelId"])
	if returnedModel == "" {
		returnedModel = asString(response["model_id"])
	}
	if returnedModel == "" {
		returnedModel = asString(options["model"])
	}
	if returnedModel == "" {
		returnedModel = asString(body["model"])
	}
	requestedModel := asString(options["model"])
	if requestedModel == "" {
		requestedModel = returnedModel
	}

	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", getNumber(usage, "input_tokens"), "token", sourceRoot+".usage.input_tokens"),
		positiveComponent("input_cache_write_tokens", subtract(cacheWrite, cacheWrite1h), "token", sourceRoot+".usage.cache_creation_input_tokens"),
		positiveComponent("input_cache_write_1h_tokens", cacheWrite1h, "token", sourceRoot+".usage.cache_creation_input_tokens_1h"),
		positiveComponent("input_cache_read_tokens", getNumber(usage, "cache_read_input_tokens"), "token", sourceRoot+".usage.cache_read_input_tokens"),
		positiveComponent("output_text_tokens", getNumber(usage, "output_tokens"), "token", sourceRoot+".usage.output_tokens"),
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

func extractCohereRerankUsage(response Object, options Object) Object {
	meta := asObject(response["meta"])
	billedUnits := asObject(meta["billed_units"])
	provider := asString(options["provider"])
	if provider == "" {
		provider = "cohere"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "cohere.rerank"
	}
	requestedModel := asString(options["model"])
	if requestedModel == "" {
		requestedModel = asString(response["model"])
	}
	returnedModel := asString(response["model"])
	if returnedModel == "" {
		returnedModel = requestedModel
	}

	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("rerank_search_units", getNumber(billedUnits, "search_units"), "search", "$.meta.billed_units.search_units"),
	}), meta)
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

func firstPresent(object Object, keys ...string) any {
	for _, key := range keys {
		if value, ok := object[key]; ok && value != nil {
			return value
		}
	}
	return json.Number("0")
}

func nestedObject(object Object, keys ...string) Object {
	for _, key := range keys {
		value := asObject(object[key])
		if len(value) > 0 {
			return value
		}
	}
	return Object{}
}

func openAIAgentsUsagePayload(response Object) (Object, string, Object) {
	usage := asObject(response["usage"])
	if len(usage) > 0 {
		return usage, "$.usage", response
	}
	for _, rootKey := range []string{"context_wrapper", "context"} {
		root := asObject(response[rootKey])
		usage := asObject(root["usage"])
		if len(usage) > 0 {
			return usage, "$." + rootKey + ".usage", root
		}
	}
	return response, "$", response
}

func extractOpenAIAgentsUsage(response Object, options Object) Object {
	usage, sourceRoot, sourceRootValue := openAIAgentsUsagePayload(response)
	cachedInput := getNumber(nestedObject(usage, "input_tokens_details"), "cached_tokens")
	reasoning := getNumber(nestedObject(usage, "output_tokens_details"), "reasoning_tokens")
	inputTokens := getNumber(usage, "input_tokens")
	outputTokens := getNumber(usage, "output_tokens")
	provider := asString(options["provider"])
	if provider == "" {
		provider = "openai"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "openai.responses"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(usage["model"])
	if returnedModel == "" {
		returnedModel = asString(sourceRootValue["model"])
	}
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
		positiveComponent("input_uncached_tokens", subtract(inputTokens, cachedInput), "token", sourceRoot+".input_tokens"),
		positiveComponent("input_cache_read_tokens", cachedInput, "token", sourceRoot+".input_tokens_details.cached_tokens"),
		positiveComponent("output_text_tokens", subtract(outputTokens, reasoning), "token", sourceRoot+".output_tokens"),
		positiveComponent("output_reasoning_tokens", reasoning, "token", sourceRoot+".output_tokens_details.reasoning_tokens"),
	}), usage)
}

func langSmithUsagePayload(response Object) (Object, string) {
	usage := asObject(response["usage_metadata"])
	if len(usage) > 0 {
		return usage, "$.usage_metadata"
	}
	usage = asObject(response["usageMetadata"])
	if len(usage) > 0 {
		return usage, "$.usageMetadata"
	}
	outputs := asObject(response["outputs"])
	usage = asObject(outputs["usage_metadata"])
	if len(usage) > 0 {
		return usage, "$.outputs.usage_metadata"
	}
	usage = asObject(outputs["usageMetadata"])
	if len(usage) > 0 {
		return usage, "$.outputs.usageMetadata"
	}
	llmOutput := asObject(outputs["llm_output"])
	usage = asObject(llmOutput["usage"])
	if len(usage) > 0 {
		return usage, "$.outputs.llm_output.usage"
	}
	for _, key := range []string{"input_tokens", "inputTokens", "prompt_tokens", "promptTokens"} {
		if _, ok := response[key]; ok {
			return response, "$"
		}
	}
	return Object{}, "$.usage_metadata"
}

func langSmithModel(response Object, usage Object, options Object) string {
	serialized := asObject(response["serialized"])
	serializedKwargs := asObject(serialized["kwargs"])
	for _, value := range []any{
		usage["model"],
		usage["model_name"],
		response["model"],
		response["model_name"],
		serializedKwargs["model"],
		serializedKwargs["model_name"],
		options["model"],
	} {
		if text := asString(value); text != "" {
			return text
		}
	}
	return ""
}

func extractLangSmithRunUsage(response Object, options Object) Object {
	usage, sourceRoot := langSmithUsagePayload(response)
	inputDetails := nestedObject(usage, "input_token_details", "inputTokenDetails")
	outputDetails := nestedObject(usage, "output_token_details", "outputTokenDetails")
	cacheRead := firstPresent(inputDetails, "cache_read", "cacheReadTokens", "cache_read_tokens")
	cacheWrite := firstPresent(inputDetails, "cache_creation", "cacheWriteTokens", "cache_write_tokens")
	inputTokens := firstPresent(usage, "input_tokens", "inputTokens", "prompt_tokens", "promptTokens")
	outputTokens := firstPresent(usage, "output_tokens", "outputTokens", "completion_tokens", "completionTokens")
	reasoning := firstPresent(outputDetails, "reasoning", "reasoningTokens", "reasoning_tokens")
	provider := asString(options["provider"])
	if provider == "" {
		provider = "unknown"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "framework.langsmith.run_usage"
	}
	requestedModel := asString(options["model"])
	returnedModel := langSmithModel(response, usage, options)
	if requestedModel == "" {
		requestedModel = returnedModel
	}

	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", subtract(subtract(inputTokens, cacheRead), cacheWrite), "token", sourceRoot+".input_tokens"),
		positiveComponent("input_cache_read_tokens", cacheRead, "token", sourceRoot+".input_token_details.cache_read"),
		positiveComponent("input_cache_write_tokens", cacheWrite, "token", sourceRoot+".input_token_details.cache_creation"),
		positiveComponent("output_text_tokens", subtract(outputTokens, reasoning), "token", sourceRoot+".output_tokens"),
		positiveComponent("output_reasoning_tokens", reasoning, "token", sourceRoot+".output_token_details.reasoning"),
	}), usage)
}

func semanticKernelUsagePayload(response Object) (Object, string) {
	for _, key := range []string{"usage", "token_usage", "tokenUsage"} {
		usage := asObject(response[key])
		if len(usage) > 0 {
			return usage, "$." + key
		}
	}
	metadata := asObject(response["metadata"])
	for _, key := range []string{"usage", "token_usage", "tokenUsage"} {
		usage := asObject(metadata[key])
		if len(usage) > 0 {
			return usage, "$.metadata." + key
		}
	}
	return response, "$"
}

func extractSemanticKernelTelemetryUsage(response Object, options Object) Object {
	usage, sourceRoot := semanticKernelUsagePayload(response)
	inputTokens := firstPresent(usage, "prompt_tokens", "promptTokens", "input_tokens", "inputTokens")
	outputTokens := firstPresent(usage, "completion_tokens", "completionTokens", "output_tokens", "outputTokens")
	metadata := asObject(response["metadata"])
	provider := asString(options["provider"])
	if provider == "" {
		provider = "unknown"
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = "framework.semantic_kernel.telemetry"
	}
	requestedModel := asString(options["model"])
	returnedModel := asString(usage["model"])
	if returnedModel == "" {
		returnedModel = asString(metadata["model"])
	}
	if returnedModel == "" {
		returnedModel = asString(response["model"])
	}
	if returnedModel == "" {
		returnedModel = requestedModel
	}
	if requestedModel == "" {
		requestedModel = returnedModel
	}
	rawUsage := Object{}
	for key, value := range usage {
		rawUsage[key] = value
	}
	for _, key := range []string{"plugin_name", "function_name", "pluginName", "functionName"} {
		if value, ok := response[key]; ok {
			rawUsage[key] = value
		}
	}

	return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
		positiveComponent("input_uncached_tokens", inputTokens, "token", sourceRoot+".prompt_tokens"),
		positiveComponent("output_text_tokens", outputTokens, "token", sourceRoot+".completion_tokens"),
	}), rawUsage)
}

func openRouterSDKResponsePayload(response Object) Object {
	nested := asObject(response["response"])
	if len(asObject(nested["usage"])) > 0 {
		return nested
	}
	return response
}

func extractOpenRouterSDKResponseUsage(response Object, options Object) Object {
	payload := openRouterSDKResponsePayload(response)
	usage := asObject(payload["usage"])
	for _, key := range []string{"inputTokens", "outputTokens", "cachedTokens", "reasoningTokens"} {
		if _, ok := usage[key]; ok {
			inputTokens := firstPresent(usage, "inputTokens", "promptTokens")
			cachedInput := firstPresent(usage, "cachedTokens", "cachedInputTokens")
			outputTokens := firstPresent(usage, "outputTokens", "completionTokens")
			reasoning := firstPresent(usage, "reasoningTokens")
			provider := asString(options["provider"])
			if provider == "" {
				provider = "openrouter"
			}
			surface := asString(options["surface"])
			if surface == "" {
				surface = "openrouter.chat_completions"
			}
			requestedModel := asString(options["model"])
			returnedModel := asString(payload["model"])
			if returnedModel == "" {
				returnedModel = requestedModel
			}
			if requestedModel == "" {
				requestedModel = returnedModel
			}
			return baseUsageLedger(provider, surface, requestedModel, returnedModel, compactComponents([]any{
				positiveComponent("input_uncached_tokens", subtract(inputTokens, cachedInput), "token", "$.usage.inputTokens"),
				positiveComponent("input_cache_read_tokens", cachedInput, "token", "$.usage.cachedTokens"),
				positiveComponent("output_text_tokens", subtract(outputTokens, reasoning), "token", "$.usage.outputTokens"),
				positiveComponent("output_reasoning_tokens", reasoning, "token", "$.usage.reasoningTokens"),
			}), usage)
		}
	}
	options["provider"] = "openrouter"
	options["surface"] = "openrouter.chat_completions"
	return extractOpenAICompatibleChatCompletionsUsage(payload, options)
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
	sourceURL := "https://www.llm-prices.com/current-v1.json"
	for _, rawPrice := range asSlice(data["prices"]) {
		price := asObject(rawPrice)
		if _, ok := price["from_date"]; ok {
			sourceURL = "https://www.llm-prices.com/historical-v1.json"
			break
		}
		if _, ok := price["to_date"]; ok {
			sourceURL = "https://www.llm-prices.com/historical-v1.json"
			break
		}
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
				"url":          sourceURL,
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

func modelsDevTiers(cost Object) []Object {
	rawTiers := []Object{}
	for _, rawTier := range asSlice(cost["tiers"]) {
		tier := asObject(rawTier)
		if len(tier) == 0 {
			continue
		}
		tierInfo := asObject(tier["tier"])
		if asString(tierInfo["type"]) == "context" && tierInfo["size"] != nil {
			rawTiers = append(rawTiers, Object{"cost": tier, "size": tierInfo["size"]})
		}
	}
	sort.SliceStable(rawTiers, func(left int, right int) bool {
		return rat(rawTiers[left]["size"]).Cmp(rat(rawTiers[right]["size"])) < 0
	})
	baseConditions := Object{}
	if len(rawTiers) > 0 {
		baseConditions["max_total_input_tokens"] = subtract(rawTiers[0]["size"], "1")
	}
	tiers := []Object{{"cost": cost, "conditions": baseConditions}}
	for index, tier := range rawTiers {
		conditions := Object{"min_total_input_tokens": numberString(tier["size"])}
		if index+1 < len(rawTiers) {
			conditions["max_total_input_tokens"] = subtract(rawTiers[index+1]["size"], "1")
		}
		tiers = append(tiers, Object{"cost": tier["cost"], "conditions": conditions})
	}
	return tiers
}

func addModelsDevCostComponents(components *[]any, cost Object, conditions Object) {
	extra := Object{}
	if len(conditions) > 0 {
		extra["conditions"] = conditions
	}
	addPriceComponent(components, "input_uncached_tokens", "token", cost["input"], "1000000", extra)
	addPriceComponent(components, "output_text_tokens", "token", cost["output"], "1000000", extra)
	addPriceComponent(components, "output_reasoning_tokens", "token", cost["reasoning"], "1000000", extra)
	addPriceComponent(components, "input_cache_read_tokens", "token", cost["cache_read"], "1000000", extra)
	addPriceComponent(components, "input_cache_write_tokens", "token", cost["cache_write"], "1000000", extra)
	addPriceComponent(components, "input_audio_tokens", "token", cost["input_audio"], "1000000", extra)
	addPriceComponent(components, "output_audio_tokens", "token", cost["output_audio"], "1000000", extra)
}

// PriceCardsFromModelsDev maps models.dev api.json data into canonical price cards.
func PriceCardsFromModelsDev(data Object) []any {
	updatedAt := asString(data["updated_at"])
	if updatedAt == "" {
		updatedAt = "1970-01-01"
	}
	cards := []any{}
	for providerID, rawProvider := range data {
		provider, ok := rawProvider.(map[string]any)
		if !ok || len(provider) == 0 {
			continue
		}
		models, ok := provider["models"].(map[string]any)
		if !ok {
			continue
		}
		for modelID, rawModel := range models {
			model, ok := rawModel.(map[string]any)
			if !ok || len(model) == 0 {
				continue
			}
			components := []any{}
			for _, tier := range modelsDevTiers(asObject(model["cost"])) {
				addModelsDevCostComponents(&components, asObject(tier["cost"]), asObject(tier["conditions"]))
			}
			if len(components) == 0 {
				continue
			}
			aliases := []any{}
			if name := asString(model["name"]); name != "" && name != modelID {
				aliases = append(aliases, name)
			}
			aliases = append(aliases, fmt.Sprintf("%s/%s", providerID, modelID))
			card := Object{
				"schema_version": "0.1",
				"id":             fmt.Sprintf("%s:%s:models-dev", providerID, modelID),
				"provider":       providerID,
				"model":          modelID,
				"aliases":        aliases,
				"components":     components,
				"source": Object{
					"name":         "models.dev",
					"url":          "https://models.dev/api.json",
					"retrieved_at": updatedAt + "T00:00:00Z",
					"license":      "MIT",
				},
				"metadata": Object{
					"models_dev": Object{
						"provider_name": provider["name"],
						"family":        model["family"],
						"limit":         model["limit"],
						"modalities":    model["modalities"],
						"reasoning":     model["reasoning"],
						"tool_call":     model["tool_call"],
						"status":        model["status"],
						"release_date":  model["release_date"],
						"last_updated":  model["last_updated"],
					},
				},
			}
			cards = append(cards, card)
		}
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

func sourceCachePriceCards(entry Object) []any {
	for _, key := range []string{"price_cards", "priceCards", "cards"} {
		if cards, ok := entry[key].([]any); ok {
			filtered := []any{}
			for _, rawCard := range cards {
				if _, ok := rawCard.(map[string]any); ok {
					filtered = append(filtered, rawCard)
				}
			}
			return filtered
		}
	}
	return []any{}
}

func sourceCacheSource(entry Object) Object {
	source := Object{}
	if rawSource, ok := entry["source"].(map[string]any); ok {
		source = rawSource
	}
	sourceType := asString(entry["type"])
	if sourceType == "" {
		sourceType = asString(entry["source_type"])
	}
	if sourceType == "" {
		sourceType = asString(entry["sourceType"])
	}
	name := asString(entry["name"])
	if name == "" {
		name = asString(source["name"])
	}
	if name == "" {
		name = sourceType
	}
	if name == "" {
		name = "source-cache"
	}
	info := Object{"name": name}
	url := asString(entry["url"])
	if url == "" {
		url = asString(source["url"])
	}
	if url != "" {
		info["url"] = url
	}
	retrievedAt := asString(entry["retrieved_at"])
	if retrievedAt == "" {
		retrievedAt = asString(entry["retrievedAt"])
	}
	if retrievedAt == "" {
		retrievedAt = asString(source["retrieved_at"])
	}
	if retrievedAt == "" {
		retrievedAt = asString(source["retrievedAt"])
	}
	if retrievedAt != "" {
		info["retrieved_at"] = retrievedAt
	}
	version := asString(entry["version"])
	if version == "" {
		version = asString(source["version"])
	}
	if version != "" {
		info["version"] = version
	}
	license := asString(entry["license"])
	if license == "" {
		license = asString(source["license"])
	}
	if license != "" {
		info["license"] = license
	}
	return info
}

func sourceCacheMetadata(data Object, entry Object, cardCount int) Object {
	metadata := Object{"card_count": cardCount}
	for outputKey, inputKeys := range map[string][]string{
		"generated_at": {"generated_at", "generatedAt"},
		"checksum":     {"checksum", "sha256"},
		"source_type":  {"type", "source_type", "sourceType"},
	} {
		for _, inputKey := range inputKeys {
			value := entry[inputKey]
			if value == nil {
				value = data[inputKey]
			}
			if asString(value) != "" {
				metadata[outputKey] = value
				break
			}
		}
	}
	return metadata
}

// PriceCardsFromSourceCache maps a RunCost source-cache envelope into
// canonical price cards while preserving retrieval metadata on each card.
func PriceCardsFromSourceCache(data Object) []any {
	entries := []any{data}
	if rawSources, ok := data["sources"].([]any); ok {
		entries = rawSources
	}
	cards := []any{}
	for _, rawEntry := range entries {
		entry, ok := rawEntry.(map[string]any)
		if !ok {
			continue
		}
		rawCards := sourceCachePriceCards(entry)
		source := sourceCacheSource(entry)
		cacheMetadata := sourceCacheMetadata(data, entry, len(rawCards))
		for _, rawCard := range rawCards {
			card := Object{}
			for key, value := range asObject(rawCard) {
				card[key] = value
			}
			if card["schema_version"] == nil {
				card["schema_version"] = "0.1"
			}
			if card["source"] == nil {
				card["source"] = source
			}
			metadata := Object{}
			if rawMetadata, ok := card["metadata"].(map[string]any); ok {
				for key, value := range rawMetadata {
					metadata[key] = value
				}
			}
			metadata["source_cache"] = cacheMetadata
			card["metadata"] = metadata
			cards = append(cards, card)
		}
	}
	return cards
}

// DefaultSourceCache returns the bundled reviewed default source-cache catalog.
func DefaultSourceCache() Object {
	var data Object
	if err := json.Unmarshal(defaultSourceCacheJSON, &data); err != nil {
		return Object{}
	}
	return data
}

// DefaultPriceCards returns price cards from the bundled reviewed default catalog.
func DefaultPriceCards() []any {
	return PriceCardsFromSourceCache(DefaultSourceCache())
}

func fileURL(path string) string {
	absolute, err := filepath.Abs(path)
	if err != nil {
		absolute = path
	}
	return (&url.URL{Scheme: "file", Path: absolute}).String()
}

func withFileSourceURL(data Object, path string) Object {
	if _, ok := data["source"].(map[string]any); ok {
		return data
	}
	copyData := Object{}
	for key, value := range data {
		copyData[key] = value
	}
	copyData["source"] = Object{"url": fileURL(path)}
	return copyData
}

type yamlLine struct {
	indent  int
	content string
}

func stripYAMLComment(line string) string {
	quote := rune(0)
	for index, char := range line {
		if (char == '\'' || char == '"') && quote == 0 {
			quote = char
		} else if char == quote {
			quote = 0
		}
		if char == '#' && quote == 0 && (index == 0 || line[index-1] == ' ' || line[index-1] == '\t') {
			return strings.TrimRight(line[:index], " \t")
		}
	}
	return strings.TrimRight(line, " \t")
}

func yamlScalar(value string) any {
	trimmed := strings.TrimSpace(value)
	switch trimmed {
	case "", "null", "Null", "NULL", "~":
		return nil
	case "true", "True", "TRUE":
		return true
	case "false", "False", "FALSE":
		return false
	}
	if len(trimmed) >= 2 {
		if (trimmed[0] == '"' && trimmed[len(trimmed)-1] == '"') || (trimmed[0] == '\'' && trimmed[len(trimmed)-1] == '\'') {
			return trimmed[1 : len(trimmed)-1]
		}
	}
	if strings.HasPrefix(trimmed, "[") && strings.HasSuffix(trimmed, "]") {
		inner := strings.TrimSpace(trimmed[1 : len(trimmed)-1])
		values := []any{}
		if inner == "" {
			return values
		}
		for _, part := range strings.Split(inner, ",") {
			values = append(values, yamlScalar(strings.TrimSpace(part)))
		}
		return values
	}
	return trimmed
}

func yamlKeyValue(content string) (string, string, error) {
	index := strings.Index(content, ":")
	if index < 0 {
		return "", "", fmt.Errorf("unsupported YAML line: %s", content)
	}
	return strings.TrimSpace(content[:index]), strings.TrimSpace(content[index+1:]), nil
}

func yamlLines(text string) []yamlLine {
	lines := []yamlLine{}
	for _, rawLine := range strings.Split(text, "\n") {
		cleaned := stripYAMLComment(strings.TrimRight(rawLine, "\r"))
		if strings.TrimSpace(cleaned) == "" {
			continue
		}
		indent := len(cleaned) - len(strings.TrimLeft(cleaned, " "))
		lines = append(lines, yamlLine{indent: indent, content: strings.TrimSpace(cleaned)})
	}
	return lines
}

func parseYAMLBlock(lines []yamlLine, start int, indent int) (any, int, error) {
	index := start
	if index >= len(lines) || lines[index].indent < indent {
		return Object{}, index, nil
	}
	if strings.HasPrefix(lines[index].content, "- ") {
		values := []any{}
		for index < len(lines) && lines[index].indent == indent && strings.HasPrefix(lines[index].content, "- ") {
			rest := strings.TrimSpace(strings.TrimPrefix(lines[index].content, "- "))
			index++
			if rest == "" {
				value, next, err := parseYAMLBlock(lines, index, indent+2)
				if err != nil {
					return nil, index, err
				}
				values = append(values, value)
				index = next
			} else if strings.Contains(rest, ":") {
				key, rawValue, err := yamlKeyValue(rest)
				if err != nil {
					return nil, index, err
				}
				item := Object{}
				if rawValue != "" {
					item[key] = yamlScalar(rawValue)
				} else {
					value, next, err := parseYAMLBlock(lines, index, indent+2)
					if err != nil {
						return nil, index, err
					}
					item[key] = value
					index = next
				}
				if index < len(lines) && lines[index].indent >= indent+2 {
					extra, next, err := parseYAMLBlock(lines, index, indent+2)
					if err != nil {
						return nil, index, err
					}
					if extraMap, ok := extra.(map[string]any); ok {
						for extraKey, extraValue := range extraMap {
							item[extraKey] = extraValue
						}
					}
					index = next
				}
				values = append(values, item)
			} else {
				values = append(values, yamlScalar(rest))
			}
		}
		return values, index, nil
	}
	mapping := Object{}
	for index < len(lines) {
		line := lines[index]
		if line.indent < indent {
			break
		}
		if line.indent > indent || strings.HasPrefix(line.content, "- ") {
			break
		}
		key, rawValue, err := yamlKeyValue(line.content)
		if err != nil {
			return nil, index, err
		}
		index++
		if rawValue != "" {
			mapping[key] = yamlScalar(rawValue)
		} else {
			value, next, err := parseYAMLBlock(lines, index, indent+2)
			if err != nil {
				return nil, index, err
			}
			mapping[key] = value
			index = next
		}
	}
	return mapping, index, nil
}

func parseSimpleYAML(text string) (Object, error) {
	lines := yamlLines(text)
	if len(lines) == 0 {
		return Object{}, nil
	}
	data, index, err := parseYAMLBlock(lines, 0, lines[0].indent)
	if err != nil {
		return nil, err
	}
	if index != len(lines) {
		return nil, fmt.Errorf("unsupported YAML structure")
	}
	result, ok := data.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("YAML root must be a mapping")
	}
	return result, nil
}

func priceCardsFromSourceData(data Object, sourceType string, path string) ([]any, error) {
	if sourceType == "" {
		sourceType = "user-pricing"
	}
	switch sourceType {
	case "llm-prices":
		return PriceCardsFromLlmPrices(data), nil
	case "litellm":
		return PriceCardsFromLiteLLM(data), nil
	case "openrouter-models":
		return PriceCardsFromOpenRouterModels(data), nil
	case "models-dev":
		return PriceCardsFromModelsDev(data), nil
	case "official-snapshot":
		return PriceCardsFromOfficialSnapshot(data), nil
	case "portkey":
		return PriceCardsFromPortkey(data), nil
	case "source-cache":
		return PriceCardsFromSourceCache(data), nil
	case "user-pricing":
		if path != "" {
			return PriceCardsFromUserPricing(withFileSourceURL(data, path)), nil
		}
		return PriceCardsFromUserPricing(data), nil
	case "helicone":
		return PriceCardsFromHelicone(data), nil
	default:
		return nil, fmt.Errorf("unsupported price source type: %s", sourceType)
	}
}

// PriceCardsFromJSONFile reads a local JSON price-source file and maps it
// through the requested source adapter.
func PriceCardsFromJSONFile(path string, sourceType string) ([]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var data Object
	if err := json.Unmarshal(raw, &data); err != nil {
		return nil, err
	}
	return priceCardsFromSourceData(data, sourceType, path)
}

// PriceCardsFromYAMLFile reads a local YAML price-source file and maps it
// through the requested source adapter.
func PriceCardsFromYAMLFile(path string, sourceType string) ([]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	data, err := parseSimpleYAML(string(raw))
	if err != nil {
		return nil, err
	}
	return priceCardsFromSourceData(data, sourceType, path)
}

func addOfficialSnapshotComponent(components *[]any, row Object, componentName string, unit string, keys []string, per string) {
	addPriceComponent(components, componentName, unit, componentAmount(row, keys...), per, nil)
}

// PriceCardsFromOfficialSnapshot maps reviewed official provider pricing
// snapshots into canonical price cards.
func PriceCardsFromOfficialSnapshot(data Object) []any {
	if rawCards, ok := data["price_cards"].([]any); ok {
		return rawCards
	}
	if rawCards, ok := data["priceCards"].([]any); ok {
		return rawCards
	}
	source := sourceInfo(data, "official-snapshot", "file://official-pricing-snapshot")
	providerDefault := asString(data["provider"])
	if providerDefault == "" {
		providerDefault = "unknown"
	}
	surfaceDefault := asString(data["surface"])
	perDefault := numberString(data["per"])
	if perDefault == "0" {
		perDefault = "1000000"
	}
	rawRows, ok := data["rows"].([]any)
	if !ok {
		rawRows, _ = data["models"].([]any)
	}
	cards := []any{}
	for _, rawRow := range rawRows {
		row, ok := rawRow.(map[string]any)
		if !ok {
			continue
		}
		model := asString(row["model"])
		if model == "" {
			model = asString(row["id"])
		}
		provider := asString(row["provider"])
		if provider == "" {
			provider = providerDefault
		}
		if model == "" || provider == "" {
			continue
		}
		per := numberString(row["per"])
		if per == "0" {
			per = perDefault
		}
		components := []any{}
		if rawComponents, ok := row["components"].([]any); ok {
			for _, rawComponent := range rawComponents {
				component, ok := rawComponent.(map[string]any)
				if !ok {
					continue
				}
				price := asObject(component["price"])
				amount := component["amount"]
				if amount == nil {
					amount = price["amount"]
				}
				componentPer := numberString(component["per"])
				if componentPer == "0" {
					componentPer = numberString(price["per"])
				}
				if componentPer == "0" {
					componentPer = per
				}
				unit := asString(component["unit"])
				if unit == "" {
					unit = "token"
				}
				addPriceComponent(&components, asString(component["usage_component"]), unit, amount, componentPer, nil)
			}
		}
		addOfficialSnapshotComponent(&components, row, "input_uncached_tokens", "token", []string{"input", "prompt", "input_uncached"}, per)
		addOfficialSnapshotComponent(&components, row, "input_cache_read_tokens", "token", []string{"cache_read", "cached_input", "input_cache_read"}, per)
		addOfficialSnapshotComponent(&components, row, "input_cache_write_tokens", "token", []string{"cache_write", "input_cache_write"}, per)
		addOfficialSnapshotComponent(&components, row, "input_cache_write_1h_tokens", "token", []string{"cache_write_1h", "input_cache_write_1h"}, per)
		addOfficialSnapshotComponent(&components, row, "output_text_tokens", "token", []string{"output", "completion", "output_text"}, per)
		addOfficialSnapshotComponent(&components, row, "output_reasoning_tokens", "token", []string{"reasoning", "thinking", "output_reasoning"}, per)
		addOfficialSnapshotComponent(&components, row, "input_audio_tokens", "token", []string{"input_audio", "audio_input"}, per)
		addOfficialSnapshotComponent(&components, row, "output_audio_tokens", "token", []string{"output_audio", "audio_output"}, per)
		addOfficialSnapshotComponent(&components, row, "request_units", "request", []string{"request", "per_request"}, "1")
		addOfficialSnapshotComponent(&components, row, "web_search_units", "search", []string{"web_search", "search"}, "1")
		if len(components) == 0 {
			continue
		}
		cardID := asString(row["price_card_id"])
		if cardID == "" {
			cardID = asString(row["priceCardId"])
		}
		if cardID == "" {
			cardID = fmt.Sprintf("%s:%s:official-snapshot", provider, model)
		}
		sourceLabel := asString(row["source_label"])
		if sourceLabel == "" {
			sourceLabel = asString(row["sourceLabel"])
		}
		card := Object{
			"schema_version": "0.1",
			"id":             cardID,
			"provider":       provider,
			"model":          model,
			"aliases":        asSlice(row["aliases"]),
			"components":     components,
			"source":         source,
			"metadata": Object{
				"official_snapshot": Object{
					"source_label": sourceLabel,
					"notes":        row["notes"],
					"capabilities": row["capabilities"],
				},
				"source_capabilities": asObject(row["capabilities"]),
			},
		}
		surface := asString(row["surface"])
		if surface == "" {
			surface = surfaceDefault
		}
		if surface != "" {
			card["surface"] = surface
		}
		if serviceTier := asString(row["service_tier"]); serviceTier != "" {
			card["service_tier"] = serviceTier
		}
		if region := asString(row["region"]); region != "" {
			card["region"] = region
		}
		if effective, ok := row["effective"].(map[string]any); ok {
			card["effective"] = effective
		}
		cards = append(cards, card)
	}
	return cards
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
		surface != "xai.responses" &&
		surface != "openai.embeddings" &&
		surface != "openai.audio_transcriptions" &&
		surface != "openai.images" &&
		surface != "openai.usage.images" &&
		surface != "openai.usage.completions" &&
		surface != "openai.usage.audio_speeches" &&
		surface != "openai.usage.audio_transcriptions" &&
		surface != "openai.usage.embeddings" &&
		surface != "openai.vector_stores" &&
		surface != "openai.usage.code_interpreter_sessions" &&
		surface != "anthropic.messages" &&
		surface != "google.gemini.generate_content" &&
		surface != "vertex.gemini.generate_content" &&
		surface != "aws.bedrock.converse" &&
		surface != "aws.bedrock.invoke_model" &&
		surface != "cohere.chat" &&
		surface != "cohere.rerank" &&
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

// FromVercelAISDKStreamFinish prices a Vercel AI SDK streamText finish/onFinish
// object by reading usage or totalUsage and applying provider price cards.
func FromVercelAISDKStreamFinish(result Object, options Object, priceCards []any, discountPolicies []any) Object {
	options["adapter"] = "vercel_ai_sdk.stream_text"
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

// FromOpenAIAgentsUsage prices an OpenAI Agents SDK usage or result-like object
// without importing the Agents SDK.
func FromOpenAIAgentsUsage(usage Object, options Object, priceCards []any, discountPolicies []any) Object {
	options["adapter"] = "openai_agents.usage"
	return FromResponse(usage, options, priceCards, discountPolicies)
}

func langSmithReportedCost(run Object) (any, bool) {
	usage := asObject(run["usage_metadata"])
	for _, value := range []any{
		run["total_cost"],
		run["totalCost"],
		run["cost"],
		usage["total_cost"],
		usage["totalCost"],
	} {
		if value != nil {
			return value, true
		}
	}
	return nil, false
}

// FromLangSmithRun prices a LangSmith run/export object and compares
// total_cost as framework-reported cost when present.
func FromLangSmithRun(run Object, options Object, priceCards []any, discountPolicies []any) Object {
	if _, exists := options["provider_reported_cost"]; !exists {
		if reportedCost, ok := langSmithReportedCost(run); ok {
			options["provider_reported_cost"] = reportedCost
			if asString(options["provider_reported_cost_mode"]) == "" {
				options["provider_reported_cost_mode"] = "compare"
			}
		}
	}
	options["adapter"] = "langsmith.run_usage"
	return FromResponse(run, options, priceCards, discountPolicies)
}

// FromSemanticKernelTelemetry prices Semantic Kernel telemetry/filter metadata
// without importing Semantic Kernel.
func FromSemanticKernelTelemetry(telemetry Object, options Object, priceCards []any, discountPolicies []any) Object {
	options["adapter"] = "semantic_kernel.telemetry"
	return FromResponse(telemetry, options, priceCards, discountPolicies)
}

func openRouterReportedCost(response Object) (any, bool) {
	payload := openRouterSDKResponsePayload(response)
	payload = openAICompatibleChatPayload(payload)
	usage := asObject(payload["usage"])
	for _, value := range []any{
		usage["cost"],
		usage["totalCost"],
		payload["cost"],
		payload["totalCost"],
	} {
		if value != nil {
			return value, true
		}
	}
	return nil, false
}

// FromOpenRouterSDKResponse prices OpenRouter-compatible SDK responses,
// including OpenAI SDK-routed chat responses and resolved Agent SDK responses.
func FromOpenRouterSDKResponse(response Object, options Object, priceCards []any, discountPolicies []any) Object {
	if _, exists := options["provider_reported_cost"]; !exists {
		if reportedCost, ok := openRouterReportedCost(response); ok {
			options["provider_reported_cost"] = reportedCost
			if asString(options["provider_reported_cost_mode"]) == "" {
				options["provider_reported_cost_mode"] = "compare"
			}
		}
	}
	options["adapter"] = "openrouter.sdk_response"
	return FromResponse(response, options, priceCards, discountPolicies)
}
