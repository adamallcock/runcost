package ledger

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

var attributionKeys = []string{"run_id", "session_id", "workflow", "tenant_id", "feature"}

func attributionString(value any) (string, bool) {
	switch typed := value.(type) {
	case string:
		return typed, true
	case bool:
		if typed {
			return "true", true
		}
		return "false", true
	case json.Number:
		return decimal(rat(typed)), true
	case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64, float32, float64:
		return decimal(rat(typed)), true
	default:
		return "", false
	}
}

// NormalizeAttribution returns schema-safe passive ledger attribution.
func NormalizeAttribution(value Object) Object {
	result := Object{}
	for _, key := range attributionKeys {
		if value != nil {
			if normalized, ok := attributionString(value[key]); ok {
				result[key] = normalized
			}
		}
	}
	if tags, ok := objectValue(value["tags"]); ok {
		keys := make([]string, 0, len(tags))
		for key := range tags {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		normalized := Object{}
		for _, key := range keys {
			if value, keep := attributionString(tags[key]); keep {
				normalized[key] = value
			}
		}
		if len(normalized) > 0 {
			result["tags"] = normalized
		}
	}
	return result
}

func cloneExpansionObject(value Object) Object {
	result := Object{}
	for key, child := range value {
		result[key] = child
	}
	return result
}

func batchError(value any, fallback string) Object {
	if object, ok := objectValue(value); ok {
		result := cloneExpansionObject(object)
		message := asString(result["message"])
		if message == "" {
			message = asString(result["detail"])
		}
		if message == "" {
			message = asString(result["status"])
		}
		if message == "" {
			message = fallback
		}
		result["message"] = message
		return result
	}
	if text := asString(value); text != "" {
		return Object{"message": text}
	}
	return Object{"message": fallback}
}

func hasBatchFailure(value any) bool {
	switch typed := value.(type) {
	case nil:
		return false
	case string:
		return strings.TrimSpace(typed) != ""
	case map[string]any:
		return len(typed) > 0
	default:
		return true
	}
}

func batchSurfaceFromEndpoint(endpoint, fallback string) string {
	if fallback != "" {
		return fallback
	}
	text := strings.ToLower(endpoint)
	switch {
	case strings.Contains(text, "responses"):
		return "openai.responses"
	case strings.Contains(text, "chat/completions"):
		return "openai.chat_completions"
	case strings.Contains(text, "embeddings"):
		return "openai.embeddings"
	case strings.Contains(text, "images"):
		return "openai.images"
	case strings.Contains(text, "audio/transcriptions"):
		return "openai.audio_transcriptions"
	default:
		return ""
	}
}

func batchItemID(item Object, index int) string {
	for _, key := range []string{"custom_id", "customId", "recordId", "record_id", "key", "id"} {
		if value := asString(item[key]); value != "" {
			return value
		}
	}
	labels := asObject(asObject(item["request"])["labels"])
	for _, key := range []string{"id", "key", "custom_id"} {
		if value := asString(labels[key]); value != "" {
			return value
		}
	}
	response := asObject(item["response"])
	for _, key := range []string{"responseId", "response_id", "id"} {
		if value := asString(response[key]); value != "" {
			return value
		}
	}
	return fmt.Sprintf("%d", index)
}

type unwrappedBatchItem struct {
	status     string
	response   Object
	err        Object
	httpStatus int
	surface    string
	metadata   Object
}

func unwrapBatchItem(item, options Object) unwrappedBatchItem {
	provider := strings.ReplaceAll(strings.ToLower(asString(options["provider"])), "_", "-")
	switch provider {
	case "openai", "kimi", "moonshot", "moonshot-ai", "dashscope", "alibaba":
		outer := asObject(item["response"])
		httpStatus, _ := optionalInt(firstNonNil(outer["status_code"], outer["statusCode"]))
		if item["error"] != nil || (httpStatus != 0 && (httpStatus < 200 || httpStatus >= 300)) {
			failure := item["error"]
			if failure == nil {
				failure = outer["body"]
			}
			return unwrappedBatchItem{status: "errored", err: batchError(failure, "OpenAI batch item failed."), httpStatus: httpStatus}
		}
		body, ok := objectValue(outer["body"])
		if !ok {
			return unwrappedBatchItem{status: "pending", err: batchError(nil, "OpenAI batch item has no response body yet."), httpStatus: httpStatus}
		}
		resolvedSurface := batchSurfaceFromEndpoint(asString(firstNonNil(options["endpoint"], item["url"])), asString(options["surface"]))
		if provider != "openai" && asString(options["surface"]) == "" {
			resolvedSurface = "kimi.chat_completions"
			if provider == "dashscope" || provider == "alibaba" {
				resolvedSurface = "dashscope.chat_completions"
			}
		}
		return unwrappedBatchItem{
			status:     "succeeded",
			response:   body,
			httpStatus: httpStatus,
			surface:    resolvedSurface,
		}
	case "anthropic":
		result := asObject(item["result"])
		kind := strings.ToLower(asString(result["type"]))
		if kind == "succeeded" {
			if message, ok := objectValue(result["message"]); ok {
				return unwrappedBatchItem{status: "succeeded", response: message, surface: "anthropic.messages"}
			}
		}
		status := "pending"
		if kind == "errored" || kind == "canceled" || kind == "expired" {
			status = kind
		}
		return unwrappedBatchItem{status: status, err: batchError(firstNonNil(result["error"], item["error"]), fmt.Sprintf("Anthropic batch item is %s.", status))}
	case "google", "gemini", "google-gemini":
		if response, ok := objectValue(item["response"]); ok {
			return unwrappedBatchItem{status: "succeeded", response: response, surface: "google.gemini.generate_content"}
		}
		if _, ok := objectValue(firstNonNil(item["usageMetadata"], item["usage_metadata"])); ok {
			return unwrappedBatchItem{status: "succeeded", response: item, surface: "google.gemini.generate_content"}
		}
		if failure := firstNonNil(item["error"], item["status"]); hasBatchFailure(failure) {
			return unwrappedBatchItem{status: "errored", err: batchError(failure, "Gemini batch item failed.")}
		}
		return unwrappedBatchItem{status: "pending", err: batchError(nil, "Gemini batch item has no response yet.")}
	case "vertex", "google-vertex", "vertex-ai":
		if response, ok := objectValue(item["response"]); ok && len(response) > 0 {
			metadata := Object{}
			for _, key := range []string{"processed_time", "processedTime"} {
				if item[key] != nil {
					metadata[key] = item[key]
				}
			}
			return unwrappedBatchItem{status: "succeeded", response: response, surface: "vertex.gemini.generate_content", metadata: metadata}
		}
		if item["status"] != nil && asString(item["status"]) != "" {
			return unwrappedBatchItem{status: "errored", err: batchError(item["status"], "Vertex batch item failed.")}
		}
		return unwrappedBatchItem{status: "pending", err: batchError(nil, "Vertex batch item has no response yet.")}
	case "bedrock", "aws-bedrock":
		if item["error"] != nil {
			return unwrappedBatchItem{status: "errored", err: batchError(item["error"], "Bedrock batch item failed.")}
		}
		if response, ok := objectValue(firstNonNil(item["modelOutput"], item["model_output"])); ok {
			surface := asString(options["surface"])
			if surface == "" {
				surface = "aws.bedrock.invoke_model"
			}
			return unwrappedBatchItem{status: "succeeded", response: response, surface: surface}
		}
		return unwrappedBatchItem{status: "pending", err: batchError(nil, "Bedrock batch item has no modelOutput yet.")}
	default:
		panic(fmt.Sprintf("unsupported batch provider: %s", asString(options["provider"])))
	}
}

func firstNonNil(values ...any) any {
	for _, value := range values {
		if value != nil {
			return value
		}
	}
	return nil
}

// FromBatchResults prices provider batch output while preserving failed items.
func FromBatchResults(items []any, options Object) Object {
	if options == nil || asString(options["provider"]) == "" {
		panic("provider is required for batch results")
	}
	normalizedProvider := strings.ReplaceAll(strings.ToLower(asString(options["provider"])), "_", "-")
	supportedProviders := map[string]bool{
		"openai": true, "kimi": true, "moonshot": true, "moonshot-ai": true, "dashscope": true,
		"alibaba": true, "anthropic": true, "google": true, "gemini": true, "google-gemini": true,
		"vertex": true, "google-vertex": true, "vertex-ai": true, "bedrock": true, "aws-bedrock": true,
	}
	if !supportedProviders[normalizedProvider] {
		panic(fmt.Sprintf("unsupported batch provider: %s", asString(options["provider"])))
	}
	attribution := NormalizeAttribution(asObject(options["attribution"]))
	var priceCards []any
	var compiledCatalog *CompiledPriceCatalog
	if rawCards, exists := options["price_cards"]; exists {
		priceCards = asSlice(rawCards)
		compiledCatalog = CompilePriceCatalog(priceCards)
	} else if rawCards, exists := options["priceCards"]; exists {
		priceCards = asSlice(rawCards)
		compiledCatalog = CompilePriceCatalog(priceCards)
	} else {
		priceCards = []any{}
		compiledCatalog = CompilePriceCatalog(priceCards)
	}
	discountPolicies := asSlice(firstNonNil(options["discount_policies"], options["discountPolicies"]))
	outputItems := []any{}
	ledgers := []any{}
	for index, rawItem := range items {
		item := asObject(rawItem)
		id := batchItemID(item, index)
		unwrapped := unwrapBatchItem(item, options)
		output := Object{"id": id, "status": unwrapped.status}
		if unwrapped.httpStatus != 0 {
			output["http_status"] = unwrapped.httpStatus
		}
		if len(unwrapped.metadata) > 0 {
			output["metadata"] = unwrapped.metadata
		}
		metadata := cloneExpansionObject(asObject(output["metadata"]))
		metadata["service_tier"] = "batch"
		metadata["batch_item_id"] = id
		if batchID := asString(firstNonNil(options["batch_id"], options["batchId"])); batchID != "" {
			metadata["batch_id"] = batchID
		}
		if endpoint := asString(options["endpoint"]); endpoint != "" {
			metadata["endpoint"] = endpoint
		}
		output["metadata"] = metadata
		if len(attribution) > 0 {
			output["attribution"] = attribution
		}
		if unwrapped.status == "succeeded" {
			if unwrapped.surface == "" {
				panic(fmt.Sprintf("surface or endpoint is required for %s batch item %s", asString(options["provider"]), id))
			}
			itemOptions := cloneExpansionObject(options)
			provider := strings.ToLower(asString(options["provider"]))
			switch provider {
			case "google", "gemini", "google-gemini":
				itemOptions["provider"] = "google"
			case "vertex", "google-vertex", "vertex-ai":
				itemOptions["provider"] = "vertex"
			case "bedrock", "aws-bedrock":
				itemOptions["provider"] = "bedrock"
			case "kimi", "moonshot", "moonshot-ai":
				itemOptions["provider"] = "kimi"
			case "dashscope", "alibaba":
				itemOptions["provider"] = "dashscope"
			}
			itemOptions["surface"] = unwrapped.surface
			context := cloneExpansionObject(asObject(options["context"]))
			context["service_tier"] = "batch"
			context["batch_item_id"] = id
			if batchID := asString(firstNonNil(options["batch_id"], options["batchId"])); batchID != "" {
				context["batch_id"] = batchID
			}
			itemOptions["context"] = context
			itemOptions["attribution"] = attribution
			ledger := fromResponseWithCatalog(unwrapped.response, itemOptions, priceCards, discountPolicies, compiledCatalog)
			output["ledger"] = ledger
			if strings.ReplaceAll(strings.ToLower(asString(options["provider"])), "_", "-") == "anthropic" {
				refusal := asObject(asObject(ledger["metadata"])["anthropic_refusal"])
				if refusal["detected"] == true {
					metadata["refusal"] = true
					metadata["requires_retry"] = refusal["requires_retry"] == true
					if recommendedModel := asString(refusal["recommended_model"]); recommendedModel != "" {
						metadata["recommended_model"] = recommendedModel
					}
					output["metadata"] = metadata
				}
			}
			ledgers = append(ledgers, ledger)
		} else {
			output["error"] = unwrapped.err
		}
		outputItems = append(outputItems, output)
	}
	aggregateOptions := Object{
		"provider":    options["provider"],
		"surface":     fmt.Sprintf("%s.batch", asString(options["provider"])),
		"model":       firstNonNil(options["model"], "multiple"),
		"mode":        firstNonNil(options["mode"], "compatibility"),
		"attribution": attribution,
	}
	aggregate := AggregateCostLedgers(ledgers, aggregateOptions)
	succeeded, pending := 0, 0
	for _, rawItem := range outputItems {
		switch asString(asObject(rawItem)["status"]) {
		case "succeeded":
			succeeded++
		case "pending":
			pending++
		}
	}
	failed := len(outputItems) - succeeded - pending
	warnings := []any{}
	if failed > 0 {
		warnings = append(warnings, Object{
			"code": "batch_items_failed", "message": fmt.Sprintf("%d batch item(s) did not succeed and remain visible in items.", failed),
			"metadata": Object{"failed": failed, "total": len(outputItems)},
		})
	}
	if pending > 0 {
		warnings = append(warnings, Object{
			"code": "batch_items_pending", "message": fmt.Sprintf("%d batch item(s) have no terminal result yet.", pending),
			"metadata": Object{"pending": pending, "total": len(outputItems)},
		})
	}
	result := Object{
		"schema_version": "0.1",
		"provider":       options["provider"],
		"surface":        fmt.Sprintf("%s.batch", asString(options["provider"])),
		"currency":       "USD",
		"items":          outputItems,
		"summary": Object{
			"total": len(outputItems), "succeeded": succeeded, "failed": failed, "pending": pending, "total_cost": aggregate["total"],
		},
		"aggregate": aggregate,
		"warnings":  warnings,
	}
	if batchID := asString(firstNonNil(options["batch_id"], options["batchId"])); batchID != "" {
		result["batch_id"] = batchID
	}
	if len(attribution) > 0 {
		result["attribution"] = attribution
	}
	return result
}

type matchAliases struct {
	aliases     []string
	unsupported bool
}

func staticMatchAliases(match Object) matchAliases {
	if value := asString(match["equals"]); value != "" {
		return matchAliases{aliases: []string{value}}
	}
	if children := asSlice(match["or"]); len(children) > 0 {
		seen := map[string]bool{}
		result := matchAliases{}
		for _, rawChild := range children {
			child := staticMatchAliases(asObject(rawChild))
			result.unsupported = result.unsupported || child.unsupported
			for _, alias := range child.aliases {
				seen[alias] = true
			}
		}
		for alias := range seen {
			result.aliases = append(result.aliases, alias)
		}
		sort.Strings(result.aliases)
		return result
	}
	return matchAliases{unsupported: len(match) > 0}
}

type tierValue struct {
	amount  any
	minimum any
	maximum any
}

func genAITierValues(value any) []tierValue {
	object, ok := objectValue(value)
	if !ok || object["base"] == nil {
		if value == nil {
			return nil
		}
		return []tierValue{{amount: value}}
	}
	tiers := []Object{}
	for _, rawTier := range asSlice(object["tiers"]) {
		tier := asObject(rawTier)
		if tier["start"] != nil {
			tiers = append(tiers, tier)
		}
	}
	sort.Slice(tiers, func(i, j int) bool { return rat(tiers[i]["start"]).Cmp(rat(tiers[j]["start"])) < 0 })
	values := []tierValue{{amount: object["base"]}}
	if len(tiers) > 0 {
		values[0].maximum = subtract(tiers[0]["start"], "1")
	}
	for index, tier := range tiers {
		entry := tierValue{amount: tier["price"], minimum: tier["start"]}
		if index+1 < len(tiers) {
			entry.maximum = subtract(tiers[index+1]["start"], "1")
		}
		values = append(values, entry)
	}
	return values
}

var genAIPriceComponents = map[string][3]string{
	"input_mtok":            {"input_uncached_tokens", "token", "1000000"},
	"cache_write_mtok":      {"input_cache_write_tokens", "token", "1000000"},
	"cache_read_mtok":       {"input_cache_read_tokens", "token", "1000000"},
	"output_mtok":           {"output_text_tokens", "token", "1000000"},
	"input_audio_mtok":      {"input_audio_tokens", "token", "1000000"},
	"cache_audio_read_mtok": {"input_cache_read_tokens", "token", "1000000"},
	"output_audio_mtok":     {"output_audio_tokens", "token", "1000000"},
	"requests_kcount":       {"request_units", "request", "1000"},
}

func convertGenAIPriceComponents(prices Object) ([]any, []string) {
	components := []any{}
	warnings := []string{}
	keys := make([]string, 0, len(prices))
	for key := range prices {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		mapping, ok := genAIPriceComponents[key]
		if !ok {
			warnings = append(warnings, fmt.Sprintf("unsupported price field retained in metadata: %s", key))
			continue
		}
		for _, tier := range genAITierValues(prices[key]) {
			component := Object{
				"usage_component": mapping[0], "unit": mapping[1],
				"price": Object{"amount": decimal(rat(tier.amount)), "currency": "USD", "per": mapping[2]},
			}
			conditions := Object{}
			if tier.minimum != nil {
				conditions["min_total_input_tokens"] = decimal(rat(tier.minimum))
			}
			if tier.maximum != nil {
				conditions["max_total_input_tokens"] = decimal(rat(tier.maximum))
			}
			if len(conditions) > 0 {
				component["conditions"] = conditions
			}
			components = append(components, component)
		}
	}
	return components, warnings
}

func previousDay(value string) string {
	parsed, err := time.Parse("2006-01-02", value)
	if err != nil {
		return value
	}
	return parsed.AddDate(0, 0, -1).Format("2006-01-02")
}

var genAIConstraintAliases = map[string][]string{
	"start_date":   {"start_date", "startDate"},
	"start_time":   {"start_time", "startTime"},
	"end_time":     {"end_time", "endTime"},
	"timezone":     {"timezone", "timeZone"},
	"days_of_week": {"days_of_week", "daysOfWeek"},
}

type genAIScheduleDetails struct {
	fields    Object
	hasTime   bool
	start     string
	end       string
	timezone  string
	days      []any
	startDate string
}

func genAIConstraintFields(value any) (Object, bool) {
	if value == nil {
		return Object{}, true
	}
	constraint, ok := objectValue(value)
	if !ok {
		return nil, false
	}
	known := map[string]bool{}
	for _, aliases := range genAIConstraintAliases {
		for _, alias := range aliases {
			known[alias] = true
		}
	}
	for key := range constraint {
		if !known[key] {
			return nil, false
		}
	}
	fields := Object{}
	for canonical, aliases := range genAIConstraintAliases {
		present := ""
		for _, alias := range aliases {
			if _, exists := constraint[alias]; !exists {
				continue
			}
			if present != "" {
				return nil, false
			}
			present = alias
		}
		if present != "" {
			fields[canonical] = constraint[present]
		}
	}
	return fields, true
}

func validGenAIDate(value string) bool {
	parsed, err := time.Parse("2006-01-02", value)
	return err == nil && parsed.Format("2006-01-02") == value
}

func genAIScheduleConstraint(value any) (genAIScheduleDetails, bool) {
	fields, ok := genAIConstraintFields(value)
	if !ok {
		return genAIScheduleDetails{}, false
	}
	startDate := ""
	if rawStartDate, exists := fields["start_date"]; exists {
		var isString bool
		startDate, isString = rawStartDate.(string)
		if !isString || !validGenAIDate(startDate) {
			return genAIScheduleDetails{}, false
		}
	}
	_, hasStart := fields["start_time"]
	_, hasEnd := fields["end_time"]
	if !hasStart && !hasEnd {
		if _, hasTimezone := fields["timezone"]; hasTimezone {
			return genAIScheduleDetails{}, false
		}
		if _, hasDays := fields["days_of_week"]; hasDays {
			return genAIScheduleDetails{}, false
		}
		return genAIScheduleDetails{fields: fields, startDate: startDate}, true
	}
	if !hasStart || !hasEnd {
		return genAIScheduleDetails{}, false
	}
	startRaw, startOK := fields["start_time"].(string)
	endRaw, endOK := fields["end_time"].(string)
	if !startOK || !endOK {
		return genAIScheduleDetails{}, false
	}
	timezoneName := "UTC"
	if rawTimezone, exists := fields["timezone"]; exists {
		var timezoneOK bool
		timezoneName, timezoneOK = rawTimezone.(string)
		if !timezoneOK || timezoneName == "" {
			return genAIScheduleDetails{}, false
		}
	}
	if _, err := time.LoadLocation(timezoneName); err != nil {
		return genAIScheduleDetails{}, false
	}
	start := strings.TrimSuffix(startRaw, "Z")
	end := strings.TrimSuffix(endRaw, "Z")
	if _, ok := timeSeconds(start); !ok {
		return genAIScheduleDetails{}, false
	}
	if _, ok := timeSeconds(end); !ok {
		return genAIScheduleDetails{}, false
	}
	var days []any
	if rawDays, exists := fields["days_of_week"]; exists {
		canonicalDays, daysOK := canonicalBillingDays(rawDays)
		if !daysOK {
			return genAIScheduleDetails{}, false
		}
		days = make([]any, len(canonicalDays))
		for index, day := range canonicalDays {
			days[index] = day
		}
	}
	return genAIScheduleDetails{
		fields:    fields,
		hasTime:   true,
		start:     start,
		end:       end,
		timezone:  timezoneName,
		days:      days,
		startDate: startDate,
	}, true
}

// PriceCardsFromGenAIPrices maps Pydantic genai-prices JSON to canonical cards.
func PriceCardsFromGenAIPrices(data any, optionValues ...Object) []any {
	options := Object{}
	if len(optionValues) > 0 && optionValues[0] != nil {
		options = optionValues[0]
	}
	providers, _ := data.([]any)
	if len(providers) == 0 {
		providers = asSlice(asObject(data)["providers"])
	}
	cards := []any{}
	for _, rawProvider := range providers {
		providerData := asObject(rawProvider)
		provider := asString(providerData["id"])
		if provider == "" {
			continue
		}
		source := Object{"name": "genai-prices"}
		if urls := asSlice(providerData["pricing_urls"]); len(urls) > 0 {
			source["url"] = asString(urls[0])
		}
		if retrieved := asString(firstNonNil(options["retrieved_at"], options["retrievedAt"])); retrieved != "" {
			source["retrieved_at"] = retrieved
		}
		if version := asString(firstNonNil(options["version"], options["source_version"], options["sourceVersion"])); version != "" {
			source["version"] = version
		}
		for _, rawModel := range asSlice(providerData["models"]) {
			modelData := asObject(rawModel)
			model := asString(modelData["id"])
			if model == "" {
				continue
			}
			match := staticMatchAliases(asObject(modelData["match"]))
			aliases := []any{}
			for _, alias := range match.aliases {
				if alias != model {
					aliases = append(aliases, alias)
				}
			}
			conditional := []any{}
			switch rawPrices := modelData["prices"].(type) {
			case []any:
				conditional = rawPrices
			case map[string]any:
				conditional = []any{Object{"prices": rawPrices}}
			}
			datedStarts := []string{}
			constraintDetails := map[int]genAIScheduleDetails{}
			for entryIndex, rawEntry := range conditional {
				entry, ok := objectValue(rawEntry)
				if !ok {
					continue
				}
				rawConstraint, exists := entry["constraint"]
				if !exists {
					rawConstraint = Object{}
				}
				details, supported := genAIScheduleConstraint(rawConstraint)
				if !supported {
					continue
				}
				constraintDetails[entryIndex] = details
				if details.startDate != "" {
					datedStarts = append(datedStarts, details.startDate)
				}
			}
			sort.Strings(datedStarts)
			timeEntryIndexes := []int{}
			timezones := map[string]bool{}
			for entryIndex, details := range constraintDetails {
				if details.hasTime {
					timeEntryIndexes = append(timeEntryIndexes, entryIndex)
					timezones[details.timezone] = true
				}
			}
			sort.Ints(timeEntryIndexes)
			timeIndexes := map[int]int{}
			var schedule Object
			if len(timeEntryIndexes) > 0 && len(timezones) == 1 {
				windows := make([]any, 0, len(timeEntryIndexes))
				for periodIndex, entryIndex := range timeEntryIndexes {
					details := constraintDetails[entryIndex]
					timeIndexes[entryIndex] = periodIndex + 1
					window := Object{
						"period": fmt.Sprintf("scheduled-%d", periodIndex+1),
						"start":  details.start,
						"end":    details.end,
					}
					if details.days != nil {
						window["days_of_week"] = details.days
					}
					windows = append(windows, window)
				}
				timezoneName := constraintDetails[timeEntryIndexes[0]].timezone
				schedule = Object{
					"timezone": timezoneName, "default_period": "default",
					"boundary_policy": "start_inclusive_end_exclusive", "windows": windows,
				}
			}
			usedCardIDs := map[string]bool{}
			for index, rawEntry := range conditional {
				entry, ok := objectValue(rawEntry)
				if !ok {
					continue
				}
				details, supported := constraintDetails[index]
				if !supported {
					continue
				}
				prices, pricesOK := objectValue(entry["prices"])
				if !pricesOK {
					continue
				}
				components, adapterWarnings := convertGenAIPriceComponents(prices)
				if len(components) == 0 {
					continue
				}
				if match.unsupported {
					adapterWarnings = append(adapterWarnings, "non-enumerable model match clause retained in metadata")
				}
				rawConstraint, constraintOK := objectValue(entry["constraint"])
				if !constraintOK {
					rawConstraint = Object{}
				}
				card := Object{
					"schema_version": "0.1", "id": fmt.Sprintf("%s:%s:genai-prices:%d", provider, model, index),
					"provider": provider, "model": model, "aliases": aliases, "components": components, "source": source,
					"metadata": Object{"genai_prices": Object{
						"provider_name": providerData["name"], "provider_match": providerData["provider_match"],
						"model_match": modelData["match"], "api_pattern": providerData["api_pattern"],
						"context_window": modelData["context_window"], "constraint": rawConstraint,
					}},
				}
				suffix := "current"
				if details.startDate != "" {
					suffix = details.startDate
					effective := Object{"from": details.startDate}
					for _, candidate := range datedStarts {
						if candidate > details.startDate {
							effective["to"] = previousDay(candidate)
							break
						}
					}
					card["effective"] = effective
				} else if len(datedStarts) > 0 && len(details.fields) == 0 {
					suffix = "historical"
					card["effective"] = Object{"to": previousDay(datedStarts[0])}
				}
				if details.hasTime {
					periodIndex, scheduled := timeIndexes[index]
					if !scheduled || len(schedule) == 0 {
						continue
					}
					suffix = fmt.Sprintf("scheduled-%d", periodIndex)
					card["pricing_period"] = suffix
					card["billing_schedule"] = schedule
				} else if len(schedule) > 0 {
					card["pricing_period"] = "default"
					card["billing_schedule"] = schedule
					if suffix == "current" {
						suffix = "default"
					} else {
						suffix += "-default"
					}
				}
				if len(adapterWarnings) > 0 {
					seenWarnings := map[string]bool{}
					uniqueWarnings := []string{}
					for _, warning := range adapterWarnings {
						if !seenWarnings[warning] {
							seenWarnings[warning] = true
							uniqueWarnings = append(uniqueWarnings, warning)
						}
					}
					sort.Strings(uniqueWarnings)
					asObject(card["metadata"])["adapter_warnings"] = uniqueWarnings
				}
				cardID := fmt.Sprintf("%s:%s:genai-prices:%s", provider, model, suffix)
				if usedCardIDs[cardID] {
					cardID = fmt.Sprintf("%s:%d", cardID, index)
				}
				usedCardIDs[cardID] = true
				card["id"] = cardID
				cards = append(cards, card)
			}
		}
	}
	return cards
}

var otelProviderMap = map[string]string{
	"openai": "openai", "anthropic": "anthropic", "aws.bedrock": "bedrock",
	"azure.ai.openai": "azure", "gcp.gen_ai": "google", "gcp.vertex_ai": "vertex", "x_ai": "xai",
}

func otelAttributes(span Object) Object {
	if attributes, ok := objectValue(span["attributes"]); ok {
		return attributes
	}
	result := Object{}
	for key, value := range span {
		if strings.Contains(key, ".") {
			result[key] = value
		}
	}
	return result
}

func otelSurface(provider, operation string) string {
	if operation == "generate_content" {
		if provider == "vertex" {
			return "vertex.gemini.generate_content"
		}
		return "google.gemini.generate_content"
	}
	if provider == "anthropic" {
		return "anthropic.messages"
	}
	if provider == "bedrock" {
		return "aws.bedrock.converse"
	}
	if operation == "embeddings" {
		return "openai.embeddings"
	}
	if provider == "openai" {
		return "openai.chat_completions"
	}
	return fmt.Sprintf("%s.chat_completions", provider)
}

func nonnegativeDifference(total any, parts ...any) string {
	value := new(big.Rat).Set(rat(total))
	for _, part := range parts {
		value.Sub(value, rat(part))
	}
	if value.Sign() < 0 {
		return "0"
	}
	return decimal(value)
}

// UsageLedgerFromOTelGenAISpan normalizes current OpenTelemetry GenAI attributes.
func UsageLedgerFromOTelGenAISpan(span, options Object) Object {
	attributes := otelAttributes(span)
	providerAttribute := asString(attributes["gen_ai.provider.name"])
	provider := asString(options["provider"])
	if provider == "" {
		provider = otelProviderMap[providerAttribute]
	}
	if provider == "" {
		provider = providerAttribute
	}
	if provider == "" {
		provider = "unknown"
	}
	operation := asString(attributes["gen_ai.operation.name"])
	if operation == "" {
		operation = "chat"
	}
	requestedModel := asString(firstNonNil(options["model"], attributes["gen_ai.request.model"], attributes["gen_ai.response.model"], "unknown"))
	returnedModel := asString(firstNonNil(attributes["gen_ai.response.model"], requestedModel))
	inputTotal := firstNonNil(attributes["gen_ai.usage.input_tokens"], 0)
	outputTotal := firstNonNil(attributes["gen_ai.usage.output_tokens"], 0)
	cacheWrite := firstNonNil(attributes["gen_ai.usage.cache_creation.input_tokens"], 0)
	cacheRead := firstNonNil(attributes["gen_ai.usage.cache_read.input_tokens"], 0)
	reasoning := firstNonNil(attributes["gen_ai.usage.reasoning.output_tokens"], 0)
	components := compactComponents([]any{
		positiveComponent("input_uncached_tokens", nonnegativeDifference(inputTotal, cacheWrite, cacheRead), "token", "$.attributes.gen_ai.usage.input_tokens"),
		positiveComponent("input_cache_read_tokens", cacheRead, "token", "$.attributes.gen_ai.usage.cache_read.input_tokens"),
		positiveComponent("input_cache_write_tokens", cacheWrite, "token", "$.attributes.gen_ai.usage.cache_creation.input_tokens"),
		positiveComponent("output_text_tokens", nonnegativeDifference(outputTotal, reasoning), "token", "$.attributes.gen_ai.usage.output_tokens"),
		positiveComponent("output_reasoning_tokens", reasoning, "token", "$.attributes.gen_ai.usage.reasoning.output_tokens"),
	})
	context := Object{}
	if tier := asString(firstNonNil(
		attributes["gen_ai.request.service_tier"], attributes["gen_ai.response.service_tier"],
		attributes["openai.response.service_tier"], attributes["openai.request.service_tier"],
	)); tier != "" {
		if provider == "openai" {
			tier = normalizeOpenAIServiceTier(tier)
		}
		context["service_tier"] = tier
	}
	if requestID := asString(firstNonNil(attributes["gen_ai.response.id"], attributes["openai.response.id"])); requestID != "" {
		context["request_id"] = requestID
	}
	if traceID := asString(firstNonNil(span["trace_id"], span["traceId"])); traceID != "" {
		context["trace_id"] = traceID
	}
	rawUsage := Object{}
	unknown := Object{}
	known := map[string]bool{
		"gen_ai.provider.name": true, "gen_ai.operation.name": true, "gen_ai.request.model": true, "gen_ai.response.model": true,
		"gen_ai.usage.input_tokens": true, "gen_ai.usage.output_tokens": true,
		"gen_ai.usage.cache_creation.input_tokens": true, "gen_ai.usage.cache_read.input_tokens": true,
		"gen_ai.usage.reasoning.output_tokens": true,
	}
	for key, value := range attributes {
		if strings.HasPrefix(key, "gen_ai.usage.") {
			rawUsage[key] = value
		}
		if strings.HasPrefix(key, "gen_ai.") && !known[key] {
			unknown[key] = value
		}
	}
	surface := asString(options["surface"])
	if surface == "" {
		surface = otelSurface(provider, operation)
	}
	ledger := Object{
		"schema_version": "0.1", "provider": provider, "surface": surface,
		"model":      Object{"requested": requestedModel, "returned": returnedModel, "billed": requestedModel, "alias_resolution": "none"},
		"components": components, "raw_usage": rawUsage,
		"metadata": Object{"otel_genai": Object{"operation": operation, "provider_attribute": providerAttribute, "unknown_attributes": unknown}},
	}
	if len(context) > 0 {
		ledger["context"] = context
	}
	if attribution := NormalizeAttribution(asObject(options["attribution"])); len(attribution) > 0 {
		ledger["attribution"] = attribution
	}
	return ledger
}

// FromOTelGenAISpan calculates a ledger directly from telemetry attributes.
func FromOTelGenAISpan(span, options Object, priceCards []any, discountPolicies []any) Object {
	usage := UsageLedgerFromOTelGenAISpan(span, options)
	return CalculateCostWithOptions(usage, priceCards, discountPolicies, options)
}

// OTelCostAttributes returns cost attributes without exporting telemetry.
func OTelCostAttributes(costLedger, options Object) Object {
	prefix := asString(options["prefix"])
	if prefix == "" {
		prefix = "runcost"
	}
	warnings := asSlice(costLedger["warnings"])
	ids := map[string]bool{}
	for _, rawComponent := range asSlice(costLedger["components"]) {
		if id := asString(asObject(rawComponent)["price_card_id"]); id != "" {
			ids[id] = true
		}
	}
	priceCardIDs := []any{}
	for id := range ids {
		priceCardIDs = append(priceCardIDs, id)
	}
	sort.Slice(priceCardIDs, func(i, j int) bool { return asString(priceCardIDs[i]) < asString(priceCardIDs[j]) })
	warningCodes := []any{}
	for _, rawWarning := range warnings {
		warningCodes = append(warningCodes, asString(asObject(rawWarning)["code"]))
	}
	return Object{
		prefix + ".cost.total":           asString(costLedger["total"]),
		prefix + ".cost.currency":        asString(costLedger["currency"]),
		prefix + ".cost.component_count": len(asSlice(costLedger["components"])),
		prefix + ".cost.warning_count":   len(warnings),
		prefix + ".cost.warning_codes":   warningCodes,
		prefix + ".cost.price_card_ids":  priceCardIDs,
	}
}

// EstimateCost prices caller-provided expected component quantities.
func EstimateCost(options Object, priceCards []any, discountPolicies []any) Object {
	components := []any{}
	if rawComponents, ok := options["components"].([]any); ok {
		for _, rawComponent := range rawComponents {
			component := cloneExpansionObject(asObject(rawComponent))
			component["quantity"] = decimal(rat(component["quantity"]))
			if asString(component["unit"]) == "" {
				component["unit"] = "token"
			}
			components = append(components, component)
		}
	} else if rawComponents, ok := objectValue(options["components"]); ok {
		keys := make([]string, 0, len(rawComponents))
		for key := range rawComponents {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		for _, key := range keys {
			components = append(components, Object{"name": key, "quantity": decimal(rat(rawComponents[key])), "unit": "token"})
		}
	}
	model := asString(options["model"])
	usage := Object{
		"schema_version": "0.1", "provider": options["provider"], "surface": options["surface"],
		"model":      Object{"requested": model, "returned": model, "billed": model, "alias_resolution": "none"},
		"components": components, "metadata": Object{"estimate": true},
	}
	if context, ok := objectValue(options["context"]); ok && len(context) > 0 {
		usage["context"] = context
	}
	if attribution := NormalizeAttribution(asObject(options["attribution"])); len(attribution) > 0 {
		usage["attribution"] = attribution
	}
	return CalculateCostWithOptions(usage, priceCards, discountPolicies, options)
}

// EvaluateBudget applies a side-effect-free budget policy to one total/ledger.
func EvaluateBudget(ledgerOrTotal any, options Object) Object {
	ledger, isLedger := objectValue(ledgerOrTotal)
	total := ledgerOrTotal
	currency := "USD"
	if isLedger {
		total = ledger["total"]
		if asString(ledger["currency"]) != "" {
			currency = asString(ledger["currency"])
		}
	}
	budget := rat(options["budget"])
	thresholdValue := firstNonNil(options["warning_threshold"], options["warningThreshold"], "0.8")
	threshold := rat(thresholdValue)
	if budget.Sign() < 0 {
		panic("budget must be non-negative")
	}
	if threshold.Sign() < 0 || threshold.Cmp(big.NewRat(1, 1)) > 0 {
		panic("warning_threshold must be between 0 and 1")
	}
	totalRat := rat(total)
	warningAmount := new(big.Rat).Mul(budget, threshold)
	status := "within_budget"
	if totalRat.Cmp(budget) > 0 {
		status = "exceeded"
	} else if budget.Sign() > 0 && totalRat.Cmp(warningAmount) >= 0 {
		status = "warning"
	}
	result := Object{
		"schema_version": "0.1", "status": status, "estimated_cost": decimal(totalRat), "budget": decimal(budget),
		"remaining": decimal(new(big.Rat).Sub(budget, totalRat)), "warning_threshold": decimal(threshold), "currency": currency,
	}
	if isLedger {
		result["ledger"] = ledger
	}
	return result
}

// ReconcileCost exposes residuals between calculated and provider totals.
func ReconcileCost(ledgerOrTotal, reportedTotal any, options Object) Object {
	ledger, isLedger := objectValue(ledgerOrTotal)
	calculatedValue := ledgerOrTotal
	currency := asString(options["currency"])
	if currency == "" {
		currency = "USD"
	}
	if isLedger {
		calculatedValue = ledger["total"]
		if asString(ledger["currency"]) != "" {
			currency = asString(ledger["currency"])
		}
	}
	calculated := rat(calculatedValue)
	reported := rat(reportedTotal)
	tolerance := rat(firstNonNil(options["tolerance"], "0"))
	if tolerance.Sign() < 0 {
		panic("tolerance must be non-negative")
	}
	residual := new(big.Rat).Sub(reported, calculated)
	absolute := new(big.Rat).Abs(residual)
	status := "mismatch"
	if absolute.Sign() == 0 {
		status = "matched"
	} else if absolute.Cmp(tolerance) <= 0 {
		status = "within_tolerance"
	}
	return Object{
		"schema_version": "0.1", "status": status, "calculated_total": decimal(calculated), "reported_total": decimal(reported),
		"signed_residual": decimal(residual), "absolute_residual": decimal(absolute), "tolerance": decimal(tolerance), "currency": currency,
	}
}

// CanonicalJSONBytes encodes deterministic JSON followed by a newline.
func CanonicalJSONBytes(value any) []byte {
	encoded, err := json.Marshal(value)
	if err != nil {
		panic(err)
	}
	return append(encoded, '\n')
}

// SHA256Bytes returns a lowercase SHA-256 digest.
func SHA256Bytes(value []byte) string {
	digest := sha256.Sum256(value)
	return fmt.Sprintf("%x", digest)
}

// VerifyCatalogManifest verifies catalog and shard files below root.
func VerifyCatalogManifest(manifest Object, root string) Object {
	entries := []any{manifest["catalog"]}
	entries = append(entries, asSlice(manifest["shards"])...)
	checked := []any{}
	_, catalogOK := objectValue(manifest["catalog"])
	_, shardsOK := manifest["shards"].([]any)
	valid := asString(manifest["schema_version"]) == "0.1" && asString(manifest["algorithm"]) == "sha256" && catalogOK && shardsOK
	for _, rawEntry := range entries {
		entry := asObject(rawEntry)
		relative := asString(entry["path"])
		expectedDigest := asString(entry["sha256"])
		if relative == "" || len(expectedDigest) != 64 {
			valid = false
			checked = append(checked, Object{"path": relative, "exists": false, "sha256": nil, "matches": false})
			continue
		}
		path := filepath.Join(root, relative)
		data, err := os.ReadFile(path)
		exists := err == nil
		digest := ""
		if exists {
			digest = SHA256Bytes(data)
		}
		matches := exists && digest == expectedDigest
		valid = valid && matches
		checked = append(checked, Object{"path": relative, "exists": exists, "sha256": digest, "matches": matches})
	}
	return Object{"schema_version": "0.1", "valid": valid, "algorithm": "sha256", "artifacts": checked}
}
