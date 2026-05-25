const MONEY_PRECISION = 18n;

function parseDecimal(value) {
  const text = String(value);
  const sign = text.startsWith("-") ? -1n : 1n;
  const unsigned = text.startsWith("-") ? text.slice(1) : text;
  const [wholeRaw, fracRaw = ""] = unsigned.split(".");
  const whole = wholeRaw || "0";
  const frac = fracRaw.replace(/0+$/, "");
  const digits = `${whole}${frac}`.replace(/^0+(?=\d)/, "") || "0";
  return {
    value: sign * BigInt(digits),
    scale: BigInt(frac.length)
  };
}

function pow10(scale) {
  return 10n ** BigInt(scale);
}

function formatDecimal(value, scale) {
  const sign = value < 0n ? "-" : "";
  const abs = value < 0n ? -value : value;
  const divisor = pow10(scale);
  const whole = abs / divisor;
  const frac = abs % divisor;
  if (frac === 0n) {
    return `${sign}${whole}`;
  }
  const fracText = frac.toString().padStart(Number(scale), "0").replace(/0+$/, "");
  return `${sign}${whole}.${fracText}`;
}

function hasOwn(object, key) {
  return Object.prototype.hasOwnProperty.call(object, key);
}

function addDecimal(left, right) {
  const a = parseDecimal(left);
  const b = parseDecimal(right);
  const scale = a.scale > b.scale ? a.scale : b.scale;
  const av = a.value * pow10(scale - a.scale);
  const bv = b.value * pow10(scale - b.scale);
  return formatDecimal(av + bv, scale);
}

function subtractDecimal(left, right) {
  const a = parseDecimal(left);
  const b = parseDecimal(right);
  const scale = a.scale > b.scale ? a.scale : b.scale;
  const av = a.value * pow10(scale - a.scale);
  const bv = b.value * pow10(scale - b.scale);
  return formatDecimal(av - bv, scale);
}

function multiplyDivideDecimal(quantity, amount, per) {
  const q = parseDecimal(quantity);
  const a = parseDecimal(amount);
  const p = parseDecimal(per);
  if (p.value === 0n) {
    throw new Error("price.per must not be zero");
  }

  const numerator = q.value * a.value * pow10(p.scale) * pow10(MONEY_PRECISION);
  const denominator = p.value * pow10(q.scale + a.scale);
  return formatDecimal(numerator / denominator, MONEY_PRECISION);
}

function multiplyDecimal(left, right) {
  return multiplyDivideDecimal(left, right, "1");
}

function billedModel(usageLedger) {
  return (
    usageLedger.model.billed ||
    usageLedger.model.returned ||
    usageLedger.model.requested
  );
}

function datePart(value) {
  if (!value) {
    return null;
  }
  return String(value).slice(0, 10);
}

function dateValue(value) {
  const part = datePart(value);
  return part ? Date.parse(`${part}T00:00:00Z`) : null;
}

function usageContext(usageLedger) {
  return usageLedger.context || {};
}

function cardIdentityMatches(usageLedger, card) {
  const model = billedModel(usageLedger);
  const modelMatches = card.model === model || (card.aliases || []).includes(model);
  const providerMatches = card.provider === usageLedger.provider;
  const surfaceMatches = !card.surface || card.surface === usageLedger.surface;
  return modelMatches && providerMatches && surfaceMatches;
}

function effectiveMatches(card, pricedAt) {
  if (!pricedAt) {
    return true;
  }
  const effective = card.effective || {};
  if (effective.from && pricedAt < effective.from) {
    return false;
  }
  if (effective.to && pricedAt > effective.to) {
    return false;
  }
  return true;
}

function cardContextMatches(usageLedger, card) {
  const context = usageContext(usageLedger);
  const pricedAt = datePart(context.priced_at);
  if (context.service_tier && card.service_tier && card.service_tier !== context.service_tier) {
    return false;
  }
  if (context.region && card.region && card.region !== context.region) {
    return false;
  }
  return effectiveMatches(card, pricedAt);
}

function cardScore(usageLedger, card) {
  const context = usageContext(usageLedger);
  let score = 0;
  if (card.surface === usageLedger.surface) score += 8;
  if (context.service_tier && card.service_tier === context.service_tier) score += 4;
  if (context.region && card.region === context.region) score += 2;
  if (card.effective) score += 1;
  return score;
}

function sourcePriorityScore(card, priceSourcePriority) {
  if (!priceSourcePriority || priceSourcePriority.length === 0) {
    return 0;
  }
  const index = priceSourcePriority.indexOf((card.source || {}).name);
  if (index === -1) {
    return 0;
  }
  return (priceSourcePriority.length - index) * 100;
}

function matchingCards(usageLedger, priceCards, priceSourcePriority = []) {
  return priceCards
    .map((card, index) => ({
      card,
      index,
      score: cardScore(usageLedger, card) + sourcePriorityScore(card, priceSourcePriority)
    }))
    .filter(({ card }) => cardIdentityMatches(usageLedger, card) && cardContextMatches(usageLedger, card))
    .sort((a, b) => b.score - a.score || a.index - b.index)
    .map(({ card }) => card);
}

function totalInputTokens(usageLedger) {
  const context = usageContext(usageLedger);
  if (context.total_input_tokens !== undefined && context.total_input_tokens !== null) {
    return parseDecimal(context.total_input_tokens);
  }
  let total = { value: 0n, scale: 0n };
  for (const component of usageLedger.components || []) {
    if (component.unit === "token" && String(component.name || "").startsWith("input_")) {
      const next = addDecimal(formatDecimal(total.value, total.scale), component.quantity);
      total = parseDecimal(next);
    }
  }
  return total;
}

function compareParsedDecimal(left, right) {
  const scale = left.scale > right.scale ? left.scale : right.scale;
  const leftValue = left.value * pow10(scale - left.scale);
  const rightValue = right.value * pow10(scale - right.scale);
  if (leftValue < rightValue) return -1;
  if (leftValue > rightValue) return 1;
  return 0;
}

function conditionsMatch(usageLedger, priceComponent) {
  const conditions = priceComponent.conditions || {};
  if (Object.keys(conditions).length === 0) {
    return true;
  }
  const totalInput = totalInputTokens(usageLedger);
  if (
    conditions.min_total_input_tokens !== undefined &&
    compareParsedDecimal(totalInput, parseDecimal(conditions.min_total_input_tokens)) < 0
  ) {
    return false;
  }
  if (
    conditions.max_total_input_tokens !== undefined &&
    compareParsedDecimal(totalInput, parseDecimal(conditions.max_total_input_tokens)) > 0
  ) {
    return false;
  }
  return true;
}

function candidatePriceComponents(priceCards, component) {
  const matches = [];
  for (const card of priceCards) {
    for (const priceComponent of card.components) {
      if (
        priceComponent.usage_component === component.name &&
        priceComponent.unit === component.unit
      ) {
        matches.push({ card, priceComponent });
      }
    }
  }

  return matches;
}

function findPriceComponents(usageLedger, priceCards, component) {
  return candidatePriceComponents(priceCards, component).filter(({ priceComponent }) => {
    return conditionsMatch(usageLedger, priceComponent);
  });
}

function longContextRuleMissingWarning(usageLedger, candidates, component) {
  if (candidates.length === 0 || !candidates.some(({ priceComponent }) => priceComponent.conditions)) {
    return null;
  }
  const totalInput = totalInputTokens(usageLedger);
  return {
    code: "long_context_rule_missing",
    message: `No long-context pricing rule matched ${component.name} at ${formatDecimal(totalInput.value, totalInput.scale)} input tokens.`
  };
}

function noMatchingCardWarning(usageLedger, priceCards) {
  const context = usageContext(usageLedger);
  const identityCards = priceCards.filter((card) => cardIdentityMatches(usageLedger, card));
  if (
    context.service_tier &&
    identityCards.length > 0 &&
    identityCards.every((card) => card.service_tier && card.service_tier !== context.service_tier)
  ) {
    return {
      code: "service_tier_unsupported",
      message: `No price card found for service tier ${context.service_tier}.`
    };
  }

  const pricedAt = datePart(context.priced_at);
  if (
    pricedAt &&
    identityCards.length > 0 &&
    !identityCards.some((card) => effectiveMatches(card, pricedAt))
  ) {
    return {
      code: "historical_price_missing",
      message: `No price card effective for ${pricedAt}.`
    };
  }

  const billedModel =
    usageLedger.model.billed ||
    usageLedger.model.returned ||
    usageLedger.model.requested;
  return {
    code: "price_not_found",
    message: `No price card matched provider, surface, model, and context for ${billedModel}.`
  };
}

function hasPriceCardForUsage(usageLedger, priceCards) {
  return priceCards.some((card) => cardIdentityMatches(usageLedger, card));
}

function policyMatches(policy, usageLedger, component) {
  const match = policy.match || {};
  const billedModel =
    usageLedger.model.billed ||
    usageLedger.model.returned ||
    usageLedger.model.requested;

  if (match.provider && match.provider !== usageLedger.provider) return false;
  if (match.surface && match.surface !== usageLedger.surface) return false;
  if (match.model && match.model !== billedModel) return false;
  const context = usageContext(usageLedger);
  if (match.service_tier && match.service_tier !== context.service_tier) return false;
  if (match.region && match.region !== context.region) return false;
  if (match.components && !match.components.includes(component.name)) return false;
  if (match.exclude_components && match.exclude_components.includes(component.name)) {
    return false;
  }
  return true;
}

function applyDiscounts(cost, policies, usageLedger, component, discountEligible) {
  if (!discountEligible) {
    return { cost, applied: [] };
  }

  let current = cost;
  const applied = [];
  const sortedPolicies = [...policies].sort((a, b) => {
    return (a.precedence ?? 100) - (b.precedence ?? 100);
  });

  for (const policy of sortedPolicies) {
    if (!policyMatches(policy, usageLedger, component)) {
      continue;
    }

    const before = current;
    const adjustment = policy.adjustment;
    if (adjustment.type === "multiplier") {
      current = multiplyDecimal(current, adjustment.value);
    } else if (adjustment.type === "percentage_discount") {
      const multiplier = subtractDecimal("1", multiplyDivideDecimal(adjustment.value, "1", "100"));
      current = multiplyDecimal(current, multiplier);
    } else if (adjustment.type === "percentage_markup") {
      const multiplier = addDecimal("1", multiplyDivideDecimal(adjustment.value, "1", "100"));
      current = multiplyDecimal(current, multiplier);
    }

    applied.push({
      policy_id: policy.id,
      component: component.name,
      amount: subtractDecimal(before, current)
    });
  }

  return { cost: current, applied };
}

function staleAfterDays(usageLedger, value) {
  if (value !== undefined && value !== null) {
    return Number(value);
  }
  const context = usageContext(usageLedger);
  const contextValue = context.stale_after_days ?? context.price_stale_after_days;
  return contextValue === undefined || contextValue === null ? null : Number(contextValue);
}

function stalePriceWarning(usageLedger, card, thresholdValue) {
  const threshold = staleAfterDays(usageLedger, thresholdValue);
  if (threshold === null) {
    return null;
  }
  const pricedAt = dateValue(usageContext(usageLedger).priced_at);
  const retrievedAt = dateValue((card.source || {}).retrieved_at);
  if (pricedAt === null || retrievedAt === null) {
    return null;
  }
  const ageDays = Math.round((pricedAt - retrievedAt) / 86400000);
  if (ageDays <= threshold) {
    return null;
  }
  return {
    code: "price_stale",
    message: `Price source ${(card.source || {}).name || "unknown"} is ${ageDays} days old; threshold is ${threshold} days.`
  };
}

function providerReportedWarning(total, providerReportedCost, providerReportedCostMode) {
  if (providerReportedCost === undefined || providerReportedCost === null || providerReportedCostMode !== "compare") {
    return null;
  }
  const providerTotal = formatDecimal(parseDecimal(providerReportedCost).value, parseDecimal(providerReportedCost).scale);
  if (providerTotal === total) {
    return null;
  }
  return {
    code: "provider_reported_cost_mismatch",
    message: `Provider reported cost ${providerTotal} differs from calculated total ${total}.`
  };
}

function applyProviderReportedCostUse(total, components, warnings, providerReportedCost, providerReportedCostMode) {
  if (providerReportedCost === undefined || providerReportedCost === null || providerReportedCostMode !== "use") {
    return total;
  }
  const parsed = parseDecimal(providerReportedCost);
  const providerTotal = formatDecimal(parsed.value, parsed.scale);
  const adjustment = subtractDecimal(providerTotal, total);
  if (adjustment !== "0") {
    components.push({
      name: "custom_units",
      quantity: adjustment,
      unit: "usd",
      unit_price: "1",
      cost: adjustment,
      price_card_id: "__provider_reported_cost__",
      discount_eligible: false,
      metadata: {
        reason: "provider_reported_cost_reconciliation",
        calculated_total: total,
        provider_reported_cost: providerTotal
      }
    });
  }
  warnings.push({
    code: "provider_reported_cost_used",
    message: `Provider reported cost ${providerTotal} used as authoritative total.`
  });
  return providerTotal;
}

function priceSourceDisagreementWarning(matches, component, priceSourcePriority) {
  if (priceSourcePriority.length > 0 || matches.length < 2) {
    return null;
  }
  const unitPrices = new Set(matches.map(({ priceComponent }) => {
    return multiplyDivideDecimal(priceComponent.price.amount, "1", priceComponent.price.per);
  }));
  if (unitPrices.size <= 1) {
    return null;
  }
  return {
    code: "price_source_disagreement",
    message: `Multiple price sources disagree for ${component.name}; using ${matches[0].card.id}.`
  };
}

function debugTraceEnabled(value) {
  return value === true;
}

function newDebugTrace() {
  return {
    schema_version: "0.1",
    decisions: [],
    summary: {
      priced_components: 0,
      unpriced_components: 0,
      warnings: 0,
      applied_discounts: 0
    }
  };
}

export function calculateCost({
  usageLedger,
  priceCards,
  discountPolicies = [],
  mode = "compatibility",
  staleAfterDays,
  stale_after_days,
  providerReportedCost,
  provider_reported_cost,
  providerReportedCostMode,
  provider_reported_cost_mode,
  priceSourcePriority,
  price_source_priority,
  debugTrace,
  debug_trace
}) {
  const components = [];
  const warnings = [];
  const appliedDiscounts = [];
  const sourceByName = new Map();
  const trace = debugTraceEnabled(debugTrace ?? debug_trace) ? newDebugTrace() : null;
  let total = "0";
  let resolvedBilledModel = billedModel(usageLedger);
  let aliasResolution = usageLedger.model.alias_resolution || "none";
  const hasModelCard = hasPriceCardForUsage(usageLedger, priceCards);
  const sourcePriority = priceSourcePriority || price_source_priority || [];
  const candidateCards = matchingCards(usageLedger, priceCards, sourcePriority);
  let warnedUnknownModel = false;
  let warnedNoMatchingCard = false;
  const warnedStaleCards = new Set();
  const staleThreshold = staleAfterDays ?? stale_after_days;
  const reportedCost = providerReportedCost ?? provider_reported_cost;
  const reportedCostMode = providerReportedCostMode ?? provider_reported_cost_mode ?? "compare";
  if (trace) {
    trace.decisions.push({
      type: "price_card_candidates",
      model: resolvedBilledModel,
      candidate_price_card_ids: candidateCards.map((card) => card.id),
      source_priority: sourcePriority
    });
  }

  for (const component of usageLedger.components) {
    if (!hasModelCard) {
      if (!warnedUnknownModel) {
        warnings.push({
          code: "unknown_model",
          message: `No price card found for ${resolvedBilledModel}.`
        });
        warnedUnknownModel = true;
      }
      if (trace) {
        trace.summary.unpriced_components += 1;
      }
      continue;
    }

    if (candidateCards.length === 0) {
      if (!warnedNoMatchingCard) {
        warnings.push(noMatchingCardWarning(usageLedger, priceCards));
        warnedNoMatchingCard = true;
      }
      if (trace) {
        trace.summary.unpriced_components += 1;
      }
      continue;
    }

    const candidates = candidatePriceComponents(candidateCards, component);
    const matches = candidates.filter(({ priceComponent }) => {
      return conditionsMatch(usageLedger, priceComponent);
    });
    if (matches.length === 0) {
      const longContextWarning = longContextRuleMissingWarning(usageLedger, candidates, component);
      if (longContextWarning) {
        warnings.push(longContextWarning);
      } else {
        warnings.push({
          code: component.name.includes("tool") ? "tool_component_unpriced" : "component_unpriced",
          message: `No price found for ${component.name} (${component.unit}).`
        });
      }
      if (trace) {
        trace.summary.unpriced_components += 1;
      }
      continue;
    }

    const disagreementWarning = priceSourceDisagreementWarning(matches, component, sourcePriority);
    if (disagreementWarning) {
      warnings.push(disagreementWarning);
    }
    const match = matches[0];
    const { card, priceComponent } = match;
    if (trace) {
      trace.decisions.push({
        type: "price_component_match",
        component: component.name,
        candidate_price_card_ids: matches.map(({ card: matchedCard }) => matchedCard.id),
        selected_price_card_id: card.id,
        selected_source: card.source.name
      });
    }
    if (card.model !== resolvedBilledModel && (card.aliases || []).includes(resolvedBilledModel)) {
      const previousBilledModel = resolvedBilledModel;
      resolvedBilledModel = card.model;
      if (aliasResolution === "none") {
        aliasResolution = "source_exact";
      }
      if (trace) {
        trace.decisions.push({
          type: "model_alias_resolution",
          from: previousBilledModel,
          to: resolvedBilledModel,
          price_card_id: card.id,
          resolution: aliasResolution
        });
      }
    }

    const baseCost = multiplyDivideDecimal(
      component.quantity,
      priceComponent.price.amount,
      priceComponent.price.per
    );
    const discountEligible = priceComponent.discount_eligible ?? true;
    const discounted = applyDiscounts(
      baseCost,
      discountPolicies,
      usageLedger,
      component,
      discountEligible
    );

    appliedDiscounts.push(...discounted.applied);
    if (trace) {
      for (const applied of discounted.applied) {
        trace.decisions.push({
          type: "discount_application",
          component: applied.component,
          policy_id: applied.policy_id,
          amount: applied.amount
        });
      }
    }
    total = addDecimal(total, discounted.cost);
    sourceByName.set(card.source.name, card.source);
    if (!warnedStaleCards.has(card.id)) {
      const staleWarning = stalePriceWarning(usageLedger, card, staleThreshold);
      if (staleWarning) {
        warnings.push(staleWarning);
        warnedStaleCards.add(card.id);
      }
    }

    components.push({
      name: component.name,
      quantity: component.quantity,
      unit: component.unit,
      unit_price: multiplyDivideDecimal(priceComponent.price.amount, "1", priceComponent.price.per),
      cost: discounted.cost,
      price_card_id: card.id,
      discount_eligible: discountEligible
    });
    if (trace) {
      trace.summary.priced_components += 1;
    }
  }

  total = applyProviderReportedCostUse(total, components, warnings, reportedCost, reportedCostMode);
  const reportedWarning = providerReportedWarning(total, reportedCost, reportedCostMode);
  if (reportedWarning) {
    warnings.push(reportedWarning);
  }
  if (trace) {
    for (const warning of warnings) {
      trace.decisions.push({
        type: "warning",
        warning_code: warning.code,
        message: warning.message
      });
    }
    trace.summary.warnings = warnings.length;
    trace.summary.applied_discounts = appliedDiscounts.length;
  }

  const result = {
    schema_version: "0.1",
    provider: usageLedger.provider,
    surface: usageLedger.surface,
    model: {
      requested: usageLedger.model.requested,
      returned: usageLedger.model.returned,
      billed: resolvedBilledModel,
      alias_resolution: aliasResolution
    },
    currency: "USD",
    components,
    total,
    price_sources: [...sourceByName.values()],
    applied_discounts: appliedDiscounts,
    warnings
  };
  if (trace) {
    result.debug_trace = trace;
  }
  if (mode === "strict" && warnings.length > 0) {
    throw new Error(`strict mode cost calculation failed: ${warnings[0].code}`);
  }
  return result;
}

function sourceKey(source) {
  return [
    source.name || "",
    source.url || "",
    source.retrieved_at || "",
    source.version || ""
  ].join("|");
}

function componentKey(component) {
  return [
    component.name || "",
    component.unit || "",
    component.unit_price || "",
    component.price_card_id || "",
    String(component.discount_eligible ?? true)
  ].join("|");
}

function streamUsageMissingWarning(expectedLedgerCount, actualLedgerCount) {
  const metadata = { actual_ledger_count: actualLedgerCount };
  if (expectedLedgerCount !== undefined && expectedLedgerCount !== null) {
    metadata.expected_ledger_count = expectedLedgerCount;
  }
  return {
    code: "stream_usage_missing",
    message: "Final streaming usage was expected but not observed; aggregate total may be incomplete.",
    metadata
  };
}

export function aggregateCostLedgers({
  costLedgers,
  cost_ledgers,
  provider = "aggregate",
  surface = "aggregate.cost_ledgers",
  model = "multiple",
  mode = "compatibility",
  expectedLedgerCount,
  expected_ledger_count,
  streamFinalUsageExpected,
  stream_final_usage_expected,
  streamFinalUsagePresent,
  stream_final_usage_present
}) {
  const ledgers = costLedgers || cost_ledgers || [];
  const componentsByKey = new Map();
  const sourceByKey = new Map();
  const appliedDiscounts = [];
  const warnings = [];
  let total = "0";

  ledgers.forEach((ledger, ledgerIndex) => {
    total = addDecimal(total, ledger.total || "0");
    for (const component of ledger.components || []) {
      const key = componentKey(component);
      if (!componentsByKey.has(key)) {
        const merged = {
          name: component.name,
          quantity: "0",
          unit: component.unit,
          unit_price: component.unit_price,
          cost: "0",
          metadata: { source_ledger_indexes: [] }
        };
        if (component.price_card_id !== undefined) merged.price_card_id = component.price_card_id;
        if (component.discount_eligible !== undefined) merged.discount_eligible = component.discount_eligible;
        componentsByKey.set(key, merged);
      }
      const merged = componentsByKey.get(key);
      merged.quantity = addDecimal(merged.quantity, component.quantity || "0");
      merged.cost = addDecimal(merged.cost, component.cost || "0");
      merged.metadata.source_ledger_indexes.push(ledgerIndex);
    }
    for (const source of ledger.price_sources || []) {
      if (!sourceByKey.has(sourceKey(source))) {
        sourceByKey.set(sourceKey(source), source);
      }
    }
    appliedDiscounts.push(...(ledger.applied_discounts || []));
    warnings.push(...(ledger.warnings || []));
  });

  const expectedCount = expectedLedgerCount ?? expected_ledger_count;
  const finalExpected = streamFinalUsageExpected ?? stream_final_usage_expected ?? false;
  const finalPresent = streamFinalUsagePresent ?? stream_final_usage_present ?? true;
  let missingStreamUsageWarned = false;
  if (finalExpected && !finalPresent) {
    warnings.push(streamUsageMissingWarning(expectedCount, ledgers.length));
    missingStreamUsageWarned = true;
  }
  if (!missingStreamUsageWarned && expectedCount !== undefined && expectedCount !== null && ledgers.length < Number(expectedCount)) {
    warnings.push(streamUsageMissingWarning(expectedCount, ledgers.length));
  }

  const metadata = {
    ledger_count: ledgers.length,
    aggregation: "cost_ledgers"
  };
  if (expectedCount !== undefined && expectedCount !== null) {
    metadata.expected_ledger_count = expectedCount;
  }

  const result = {
    schema_version: "0.1",
    provider,
    surface,
    model: {
      requested: model,
      returned: model,
      billed: model,
      alias_resolution: "none"
    },
    currency: "USD",
    components: [...componentsByKey.values()],
    total,
    price_sources: [...sourceByKey.values()],
    applied_discounts: appliedDiscounts,
    warnings,
    metadata
  };
  if (mode === "strict" && warnings.length > 0) {
    throw new Error(`strict mode cost aggregation failed: ${warnings[0].code}`);
  }
  return result;
}

function numberString(value) {
  return String(value ?? 0);
}

function positiveComponent(name, quantity, unit, sourcePath) {
  const decimal = parseDecimal(quantity);
  if (decimal.value <= 0n) {
    return null;
  }
  return {
    name,
    quantity: numberString(quantity),
    unit,
    source_path: sourcePath
  };
}

function compactComponents(components) {
  return components.filter(Boolean);
}

function baseUsageLedger({ provider, surface, requestedModel, returnedModel, components, rawUsage }) {
  return {
    schema_version: "0.1",
    provider,
    surface,
    model: {
      requested: requestedModel || returnedModel,
      returned: returnedModel,
      billed: returnedModel || requestedModel,
      alias_resolution: "none"
    },
    components,
    raw_usage: rawUsage
  };
}

export function extractOpenAIResponsesUsage(response, options = {}) {
  const usage = response.usage || {};
  const cachedInput = usage.input_tokens_details?.cached_tokens || 0;
  const reasoning = usage.output_tokens_details?.reasoning_tokens || 0;
  const input = usage.input_tokens || 0;
  const output = usage.output_tokens || 0;

  const toolComponents = [];
  for (const item of response.output || []) {
    if (item.type === "web_search_call") {
      toolComponents.push(positiveComponent("web_search_units", 1, "search", "$.output[*].type"));
    } else if (item.type === "file_search_call") {
      toolComponents.push(positiveComponent("file_search_units", 1, "call", "$.output[*].type"));
    } else if (item.type === "code_interpreter_call") {
      toolComponents.push(positiveComponent("code_interpreter_call_units", 1, "call", "$.output[*].type"));
    }
  }

  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.responses",
    requestedModel: options.model || response.model,
    returnedModel: response.model,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", input - cachedInput, "token", "$.usage.input_tokens"),
      positiveComponent("input_cache_read_tokens", cachedInput, "token", "$.usage.input_tokens_details.cached_tokens"),
      positiveComponent("output_text_tokens", output - reasoning, "token", "$.usage.output_tokens"),
      positiveComponent("output_reasoning_tokens", reasoning, "token", "$.usage.output_tokens_details.reasoning_tokens"),
      ...toolComponents
    ])
  });
}

const OPENAI_COMPATIBLE_CHAT_PROVIDERS = {
  "openai.chat_completions": "openai",
  "openrouter.chat_completions": "openrouter",
  "groq.chat_completions": "groq",
  "xai.chat_completions": "xai",
  "mistral.chat_completions": "mistral",
  "deepseek.chat_completions": "deepseek",
  "azure.openai.chat_completions": "azure",
  "huggingface.chat_completions": "huggingface"
};

function openAICompatibleCachedInput(usage) {
  if (hasOwn(usage.prompt_tokens_details || {}, "cached_tokens")) {
    return {
      value: usage.prompt_tokens_details.cached_tokens || 0,
      sourcePath: "$.usage.prompt_tokens_details.cached_tokens"
    };
  }
  if (hasOwn(usage, "prompt_cache_hit_tokens")) {
    return {
      value: usage.prompt_cache_hit_tokens || 0,
      sourcePath: "$.usage.prompt_cache_hit_tokens"
    };
  }
  return {
    value: 0,
    sourcePath: "$.usage.prompt_tokens_details.cached_tokens"
  };
}

function openAICompatibleReasoningOutput(usage) {
  if (hasOwn(usage.completion_tokens_details || {}, "reasoning_tokens")) {
    return {
      value: usage.completion_tokens_details.reasoning_tokens || 0,
      sourcePath: "$.usage.completion_tokens_details.reasoning_tokens"
    };
  }
  if (hasOwn(usage.output_tokens_details || {}, "reasoning_tokens")) {
    return {
      value: usage.output_tokens_details.reasoning_tokens || 0,
      sourcePath: "$.usage.output_tokens_details.reasoning_tokens"
    };
  }
  return {
    value: 0,
    sourcePath: "$.usage.completion_tokens_details.reasoning_tokens"
  };
}

export function extractOpenAICompatibleChatCompletionsUsage(response, options = {}) {
  const usage = response.usage || {};
  const cachedInput = openAICompatibleCachedInput(usage);
  const reasoning = openAICompatibleReasoningOutput(usage);
  const prompt = usage.prompt_tokens ?? ((usage.prompt_cache_hit_tokens || 0) + (usage.prompt_cache_miss_tokens || 0));
  const completion = usage.completion_tokens || 0;
  const surface = options.surface || "openai.chat_completions";

  return baseUsageLedger({
    provider: options.provider || OPENAI_COMPATIBLE_CHAT_PROVIDERS[surface] || "openai",
    surface,
    requestedModel: options.model || response.model,
    returnedModel: response.model,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", prompt - cachedInput.value, "token", "$.usage.prompt_tokens"),
      positiveComponent("input_cache_read_tokens", cachedInput.value, "token", cachedInput.sourcePath),
      positiveComponent("output_text_tokens", completion - reasoning.value, "token", "$.usage.completion_tokens"),
      positiveComponent("output_reasoning_tokens", reasoning.value, "token", reasoning.sourcePath)
    ])
  });
}

export function extractOpenAIChatCompletionsUsage(response, options = {}) {
  return extractOpenAICompatibleChatCompletionsUsage(response, {
    provider: "openai",
    surface: "openai.chat_completions",
    ...options
  });
}

export function extractOpenRouterChatCompletionsUsage(response, options = {}) {
  return extractOpenAICompatibleChatCompletionsUsage(response, {
    provider: "openrouter",
    surface: "openrouter.chat_completions",
    ...options
  });
}

export function extractAnthropicMessagesUsage(response, options = {}) {
  const usage = response.usage || {};
  const input = usage.input_tokens || 0;
  const cacheWrite = usage.cache_creation_input_tokens || 0;
  const cacheWrite1h = usage.cache_creation_input_tokens_1h || 0;
  const cacheRead = usage.cache_read_input_tokens || 0;
  const output = usage.output_tokens || 0;

  return baseUsageLedger({
    provider: options.provider || "anthropic",
    surface: options.surface || "anthropic.messages",
    requestedModel: options.model || response.model,
    returnedModel: response.model,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", input, "token", "$.usage.input_tokens"),
      positiveComponent("input_cache_write_tokens", cacheWrite - cacheWrite1h, "token", "$.usage.cache_creation_input_tokens"),
      positiveComponent("input_cache_write_1h_tokens", cacheWrite1h, "token", "$.usage.cache_creation_input_tokens_1h"),
      positiveComponent("input_cache_read_tokens", cacheRead, "token", "$.usage.cache_read_input_tokens"),
      positiveComponent("output_text_tokens", output, "token", "$.usage.output_tokens")
    ])
  });
}

const GEMINI_INPUT_MODALITY_COMPONENTS = {
  MODALITY_UNSPECIFIED: "input_uncached_tokens",
  TEXT: "input_uncached_tokens",
  DOCUMENT: "input_uncached_tokens",
  IMAGE: "input_image_tokens",
  AUDIO: "input_audio_tokens",
  VIDEO: "input_video_tokens"
};

const GEMINI_OUTPUT_MODALITY_COMPONENTS = {
  MODALITY_UNSPECIFIED: "output_text_tokens",
  TEXT: "output_text_tokens",
  DOCUMENT: "output_text_tokens",
  IMAGE: "output_image_tokens",
  AUDIO: "output_audio_tokens",
  VIDEO: "output_video_tokens"
};

const GEMINI_INPUT_COMPONENT_ORDER = [
  "input_uncached_tokens",
  "input_image_tokens",
  "input_audio_tokens",
  "input_video_tokens"
];

const GEMINI_OUTPUT_COMPONENT_ORDER = [
  "output_text_tokens",
  "output_image_tokens",
  "output_audio_tokens",
  "output_video_tokens"
];

function isPositiveDecimal(value) {
  return parseDecimal(value).value > 0n;
}

function addGeminiCount(counts, modality, quantity) {
  const parsed = parseDecimal(quantity ?? 0);
  if (parsed.value === 0n) {
    return;
  }
  counts[modality] = addDecimal(counts[modality] || "0", quantity ?? 0);
}

function geminiModalityCounts(details) {
  const counts = {};
  if (!Array.isArray(details)) {
    return counts;
  }
  for (const detail of details) {
    if (!detail || typeof detail !== "object") {
      continue;
    }
    const modality = String(detail.modality || "MODALITY_UNSPECIFIED").toUpperCase();
    addGeminiCount(counts, modality, detail.tokenCount || 0);
  }
  return counts;
}

function geminiSumCounts(counts) {
  return Object.values(counts).reduce((total, quantity) => addDecimal(total, quantity), "0");
}

function geminiNetInputCounts(promptCounts, cacheCounts, toolCounts) {
  const counts = {};
  const modalities = new Set([
    ...Object.keys(promptCounts),
    ...Object.keys(cacheCounts),
    ...Object.keys(toolCounts)
  ]);
  for (const modality of modalities) {
    const prompt = promptCounts[modality] || "0";
    const cache = cacheCounts[modality] || "0";
    const tool = toolCounts[modality] || "0";
    counts[modality] = addDecimal(subtractDecimal(prompt, cache), tool);
  }
  return counts;
}

function geminiComponentQuantities(counts, modalityComponents, fallbackComponent) {
  const quantities = {};
  for (const [modality, quantity] of Object.entries(counts)) {
    const component = modalityComponents[modality] || fallbackComponent;
    quantities[component] = addDecimal(quantities[component] || "0", quantity);
  }
  return quantities;
}

function geminiOrderedComponents(quantities, order, sourcePath) {
  return order.map((component) => (
    positiveComponent(component, quantities[component] || "0", "token", sourcePath)
  ));
}

export function extractGeminiGenerateContentUsage(response, options = {}) {
  const usage = response.usageMetadata || {};
  const cachedInput = usage.cachedContentTokenCount || 0;
  const prompt = usage.promptTokenCount || 0;
  const candidates = usage.candidatesTokenCount || 0;
  const thoughts = usage.thoughtsTokenCount || 0;

  const promptCounts = geminiModalityCounts(usage.promptTokensDetails);
  const cacheCounts = geminiModalityCounts(usage.cacheTokensDetails);
  const toolCounts = geminiModalityCounts(usage.toolUsePromptTokensDetails);
  const candidateCounts = geminiModalityCounts(usage.candidatesTokensDetails);

  const toolPrompt = hasOwn(usage, "toolUsePromptTokenCount")
    ? usage.toolUsePromptTokenCount || 0
    : geminiSumCounts(toolCounts);
  const toolRemainder = subtractDecimal(toolPrompt, geminiSumCounts(toolCounts));
  if (isPositiveDecimal(toolRemainder)) {
    addGeminiCount(toolCounts, "TEXT", toolRemainder);
  }

  const detailSafeForInput = Object.keys(promptCounts).length > 0 &&
    (!isPositiveDecimal(cachedInput) || Object.keys(cacheCounts).length > 0);
  let inputComponents;
  let cacheRead = cachedInput;
  if (detailSafeForInput) {
    inputComponents = geminiOrderedComponents(
      geminiComponentQuantities(
        geminiNetInputCounts(promptCounts, cacheCounts, toolCounts),
        GEMINI_INPUT_MODALITY_COMPONENTS,
        "input_uncached_tokens"
      ),
      GEMINI_INPUT_COMPONENT_ORDER,
      "$.usageMetadata.promptTokensDetails"
    );
    cacheRead = isPositiveDecimal(cachedInput) ? cachedInput : geminiSumCounts(cacheCounts);
  } else {
    inputComponents = [
      positiveComponent(
        "input_uncached_tokens",
        addDecimal(subtractDecimal(prompt, cachedInput), toolPrompt),
        "token",
        "$.usageMetadata.promptTokenCount"
      )
    ];
  }

  let outputComponents;
  if (Object.keys(candidateCounts).length > 0) {
    outputComponents = geminiOrderedComponents(
      geminiComponentQuantities(
        candidateCounts,
        GEMINI_OUTPUT_MODALITY_COMPONENTS,
        "output_text_tokens"
      ),
      GEMINI_OUTPUT_COMPONENT_ORDER,
      "$.usageMetadata.candidatesTokensDetails"
    );
  } else {
    outputComponents = [
      positiveComponent("output_text_tokens", candidates, "token", "$.usageMetadata.candidatesTokenCount")
    ];
  }

  return baseUsageLedger({
    provider: options.provider || "google",
    surface: options.surface || "google.gemini.generate_content",
    requestedModel: options.model || response.modelVersion,
    returnedModel: response.modelVersion || options.model,
    rawUsage: usage,
    components: compactComponents([
      ...inputComponents.slice(0, 1),
      positiveComponent("input_cache_read_tokens", cacheRead, "token", "$.usageMetadata.cachedContentTokenCount"),
      ...inputComponents.slice(1),
      ...outputComponents.slice(0, 1),
      positiveComponent("output_reasoning_tokens", thoughts, "token", "$.usageMetadata.thoughtsTokenCount"),
      ...outputComponents.slice(1)
    ])
  });
}

export function extractBedrockConverseUsage(response, options = {}) {
  const usage = response.usage || {};
  const cacheRead = usage.cacheReadInputTokens || 0;
  const cacheWrite = usage.cacheWriteInputTokens || 0;
  const cacheWrite1h = (usage.cacheDetails || [])
    .filter((detail) => detail.ttl === "1h")
    .reduce((total, detail) => total + (detail.inputTokens || 0), 0);
  const input = usage.inputTokens || 0;
  const output = usage.outputTokens || 0;
  const returnedModel = response.modelId || options.model;

  return baseUsageLedger({
    provider: options.provider || "bedrock",
    surface: options.surface || "aws.bedrock.converse",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", input - cacheRead - cacheWrite, "token", "$.usage.inputTokens"),
      positiveComponent("input_cache_write_tokens", cacheWrite - cacheWrite1h, "token", "$.usage.cacheWriteInputTokens"),
      positiveComponent("input_cache_write_1h_tokens", cacheWrite1h, "token", "$.usage.cacheDetails"),
      positiveComponent("input_cache_read_tokens", cacheRead, "token", "$.usage.cacheReadInputTokens"),
      positiveComponent("output_text_tokens", output, "token", "$.usage.outputTokens")
    ])
  });
}

function cohereChatUsagePayload(response) {
  if (response.usage && hasOwn(response.usage, "billed_units")) {
    return {
      usage: response.usage,
      sourceRoot: "$.usage"
    };
  }
  return {
    usage: response.meta || {},
    sourceRoot: "$.meta"
  };
}

export function extractCohereChatUsage(response, options = {}) {
  const { usage, sourceRoot } = cohereChatUsagePayload(response);
  const billedUnits = usage.billed_units || {};
  const returnedModel = response.model || options.model;

  return baseUsageLedger({
    provider: options.provider || "cohere",
    surface: options.surface || "cohere.chat",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", billedUnits.input_tokens || 0, "token", `${sourceRoot}.billed_units.input_tokens`),
      positiveComponent("output_text_tokens", billedUnits.output_tokens || 0, "token", `${sourceRoot}.billed_units.output_tokens`)
    ])
  });
}

export function extractLangChainChatUsage(response, options = {}) {
  const usage = response.usage_metadata || response.usageMetadata || {};
  const inputDetails = usage.input_token_details || {};
  const outputDetails = usage.output_token_details || {};
  const cacheRead = inputDetails.cache_read || 0;
  const cacheWrite = inputDetails.cache_creation || 0;
  const inputTokens = usage.input_tokens || 0;
  const outputTokens = usage.output_tokens || 0;
  const reasoning = outputDetails.reasoning || 0;
  const metadata = response.response_metadata || {};
  const returnedModel = metadata.model_name || metadata.model || options.model;

  return baseUsageLedger({
    provider: options.provider || "unknown",
    surface: options.surface || "framework.langchain.chat",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", inputTokens - cacheRead - cacheWrite, "token", "$.usage_metadata.input_tokens"),
      positiveComponent("input_cache_read_tokens", cacheRead, "token", "$.usage_metadata.input_token_details.cache_read"),
      positiveComponent("input_cache_write_tokens", cacheWrite, "token", "$.usage_metadata.input_token_details.cache_creation"),
      positiveComponent("output_text_tokens", outputTokens - reasoning, "token", "$.usage_metadata.output_tokens"),
      positiveComponent("output_reasoning_tokens", reasoning, "token", "$.usage_metadata.output_token_details.reasoning")
    ])
  });
}

function vercelAISDKUsagePayload(response) {
  if (response.totalUsage) {
    return {
      usage: response.totalUsage,
      sourceRoot: "$.totalUsage"
    };
  }
  return {
    usage: response.usage || {},
    sourceRoot: "$.usage"
  };
}

export function extractVercelAISDKUsage(response, options = {}) {
  const { usage, sourceRoot } = vercelAISDKUsagePayload(response);
  const inputDetails = usage.inputTokenDetails || {};
  const outputDetails = usage.outputTokenDetails || {};
  const cacheRead = inputDetails.cacheReadTokens ?? usage.cachedInputTokens ?? 0;
  const cacheWrite = inputDetails.cacheWriteTokens || 0;
  const inputTokens = usage.inputTokens || 0;
  const uncached = inputDetails.noCacheTokens ?? (inputTokens - cacheRead - cacheWrite);
  const outputTokens = usage.outputTokens || 0;
  const reasoning = outputDetails.reasoningTokens ?? usage.reasoningTokens ?? 0;
  const textTokens = outputDetails.textTokens ?? (outputTokens - reasoning);
  const modelMetadata = response.model || {};
  const responseMetadata = response.response || {};
  const returnedModel = responseMetadata.modelId || modelMetadata.modelId || options.model;

  return baseUsageLedger({
    provider: options.provider || modelMetadata.provider || "unknown",
    surface: options.surface || "framework.vercel_ai_sdk",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", uncached, "token", `${sourceRoot}.inputTokenDetails.noCacheTokens`),
      positiveComponent("input_cache_read_tokens", cacheRead, "token", `${sourceRoot}.inputTokenDetails.cacheReadTokens`),
      positiveComponent("input_cache_write_tokens", cacheWrite, "token", `${sourceRoot}.inputTokenDetails.cacheWriteTokens`),
      positiveComponent("output_text_tokens", textTokens, "token", `${sourceRoot}.outputTokenDetails.textTokens`),
      positiveComponent("output_reasoning_tokens", reasoning, "token", `${sourceRoot}.outputTokenDetails.reasoningTokens`)
    ])
  });
}

export function extractLlamaIndexTokenCounterUsage(response, options = {}) {
  const events = response.llm_token_counts || [];
  const promptTokens = events.length
    ? events.reduce((total, event) => total + (event.prompt_token_count || 0), 0)
    : (response.prompt_llm_token_count || 0);
  const completionTokens = events.length
    ? events.reduce((total, event) => total + (event.completion_token_count || 0), 0)
    : (response.completion_llm_token_count || 0);
  const returnedModel = response.model || options.model;

  return baseUsageLedger({
    provider: options.provider || "unknown",
    surface: options.surface || "framework.llamaindex.token_counter",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: response,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", promptTokens, "token", "$.llm_token_counts[*].prompt_token_count"),
      positiveComponent("output_text_tokens", completionTokens, "token", "$.llm_token_counts[*].completion_token_count")
    ])
  });
}

export function extractUsageLedger(response, options = {}) {
  const adapter = options.adapter || options.framework;
  if (adapter === "langchain.chat_message") {
    return extractLangChainChatUsage(response, options);
  }
  if (adapter === "vercel_ai_sdk.generate_text") {
    return extractVercelAISDKUsage(response, options);
  }
  if (adapter === "llamaindex.token_counter") {
    return extractLlamaIndexTokenCounterUsage(response, options);
  }

  const surface = options.surface;
  if (surface === "openai.responses") {
    return extractOpenAIResponsesUsage(response, options);
  }
  if (surface === "openai.chat_completions") {
    return extractOpenAIChatCompletionsUsage(response, options);
  }
  if (hasOwn(OPENAI_COMPATIBLE_CHAT_PROVIDERS, surface)) {
    return extractOpenAICompatibleChatCompletionsUsage(response, options);
  }
  if (surface === "anthropic.messages") {
    return extractAnthropicMessagesUsage(response, options);
  }
  if (surface === "google.gemini.generate_content" || surface === "vertex.gemini.generate_content") {
    return extractGeminiGenerateContentUsage(response, options);
  }
  if (surface === "aws.bedrock.converse") {
    return extractBedrockConverseUsage(response, options);
  }
  if (surface === "cohere.chat") {
    return extractCohereChatUsage(response, options);
  }
  throw new Error(`Unsupported surface: ${surface}`);
}

function unsupportedSurfaceLedger(response, options = {}) {
  const surface = options.surface || "unknown";
  const provider = options.provider || "unknown";
  const model = options.model || response.model || "unknown";
  return {
    schema_version: "0.1",
    provider,
    surface,
    model: {
      requested: model,
      returned: response.model,
      billed: model,
      alias_resolution: "unknown"
    },
    currency: "USD",
    components: [],
    total: "0",
    price_sources: [],
    applied_discounts: [],
    warnings: [
      {
        code: "unknown_surface",
        message: `Unsupported surface: ${surface}.`
      }
    ]
  };
}

export function priceCardsFromLlmPrices(data, options = {}) {
  const retrievedAt = options.retrievedAt || `${data.updated_at || "1970-01-01"}T00:00:00Z`;
  const sourceUrl = options.sourceUrl || "https://www.llm-prices.com/current-v1.json";
  return (data.prices || []).flatMap((price) => {
    const components = [
      {
        usage_component: "input_uncached_tokens",
        unit: "token",
        price: { amount: numberString(price.input), currency: "USD", per: "1000000" }
      },
      {
        usage_component: "output_text_tokens",
        unit: "token",
        price: { amount: numberString(price.output), currency: "USD", per: "1000000" }
      }
    ];
    if (price.input_cached !== null && price.input_cached !== undefined) {
      components.push({
        usage_component: "input_cache_read_tokens",
        unit: "token",
        price: { amount: numberString(price.input_cached), currency: "USD", per: "1000000" }
      });
    }

    return [{
      schema_version: "0.1",
      id: `${price.vendor}:${price.id}:llm-prices`,
      provider: price.vendor,
      model: price.id,
      aliases: [price.name].filter(Boolean),
      effective: {
        from: price.from_date ?? null,
        to: price.to_date ?? null
      },
      components,
      source: {
        name: "llm-prices",
        url: sourceUrl,
        retrieved_at: retrievedAt
      }
    }];
  });
}

function addPriceComponent(components, usageComponent, unit, amount, per = "1", extra = {}) {
  if (amount === null || amount === undefined) {
    return;
  }
  components.push({
    usage_component: usageComponent,
    unit,
    price: { amount: numberString(amount), currency: "USD", per },
    ...extra
  });
}

export function priceCardsFromLiteLLM(data, options = {}) {
  const retrievedAt = options.retrievedAt || `${data.updated_at || "1970-01-01"}T00:00:00Z`;
  const sourceUrl = options.sourceUrl || "https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json";
  return Object.entries(data).flatMap(([model, config]) => {
    if (model === "sample_spec" || model === "updated_at" || typeof config !== "object" || config === null) {
      return [];
    }
    const provider = config.litellm_provider || options.provider || "unknown";
    const components = [];
    addPriceComponent(components, "input_uncached_tokens", "token", config.input_cost_per_token);
    addPriceComponent(components, "output_text_tokens", "token", config.output_cost_per_token);
    addPriceComponent(components, "input_cache_read_tokens", "token", config.cache_read_input_token_cost);
    addPriceComponent(components, "input_cache_write_tokens", "token", config.cache_creation_input_token_cost);
    addPriceComponent(components, "input_cache_write_1h_tokens", "token", config.cache_creation_input_token_cost_1h);
    addPriceComponent(components, "output_reasoning_tokens", "token", config.output_cost_per_reasoning_token || config.output_cost_per_token);
    if (components.length === 0) return [];
    return [{
      schema_version: "0.1",
      id: `${provider}:${model}:litellm`,
      provider,
      model,
      components,
      source: {
        name: "litellm",
        url: sourceUrl,
        retrieved_at: retrievedAt
      }
    }];
  });
}

export function priceCardsFromPortkey(data, options = {}) {
  const retrievedAt = options.retrievedAt || `${data.updated_at || "1970-01-01"}T00:00:00Z`;
  const sourceUrl = options.sourceUrl || "https://github.com/Portkey-AI/models";
  const provider = data.provider || options.provider || "unknown";
  return Object.entries(data.models || {}).flatMap(([model, entry]) => {
    const pricing = entry.pricing || entry.pay_as_you_go || {};
    const components = [];
    addPriceComponent(components, "input_uncached_tokens", "token", pricing.request_token === undefined ? undefined : multiplyDivideDecimal(pricing.request_token, "1", "100"));
    addPriceComponent(components, "output_text_tokens", "token", pricing.response_token === undefined ? undefined : multiplyDivideDecimal(pricing.response_token, "1", "100"));
    addPriceComponent(components, "input_cache_read_tokens", "token", pricing.cache_read_input_token === undefined ? undefined : multiplyDivideDecimal(pricing.cache_read_input_token, "1", "100"));
    addPriceComponent(components, "input_cache_write_tokens", "token", pricing.cache_write_input_token === undefined ? undefined : multiplyDivideDecimal(pricing.cache_write_input_token, "1", "100"));
    const additional = pricing.additional_units || {};
    addPriceComponent(components, "output_reasoning_tokens", "token", additional.thinking_token === undefined ? undefined : multiplyDivideDecimal(additional.thinking_token, "1", "100"));
    addPriceComponent(components, "web_search_units", "search", additional.web_search === undefined ? undefined : multiplyDivideDecimal(additional.web_search, "1", "100"));
    if (components.length === 0) return [];
    return [{
      schema_version: "0.1",
      id: `${provider}:${model}:portkey`,
      provider,
      model,
      components,
      source: {
        name: "portkey",
        url: sourceUrl,
        retrieved_at: retrievedAt
      }
    }];
  });
}

function openRouterPricingTiers(pricing) {
  if (Array.isArray(pricing)) {
    return pricing.filter((tier) => tier && typeof tier === "object");
  }
  if (pricing && typeof pricing === "object") {
    return [pricing];
  }
  return [];
}

function openRouterTierConditions(tiers, index) {
  const tier = tiers[index];
  const conditions = {};
  if (tier.min_context !== undefined && tier.min_context !== null) {
    conditions.min_total_input_tokens = numberString(tier.min_context);
  }
  if (tier.min_context === undefined || tier.min_context === null) {
    const nextTier = tiers.slice(index + 1).find((candidate) => (
      candidate.min_context !== undefined && candidate.min_context !== null
    ));
    if (nextTier) {
      conditions.max_total_input_tokens = subtractDecimal(nextTier.min_context, "1");
    }
  }
  return Object.keys(conditions).length > 0 ? { conditions } : {};
}

function thresholdTierConditions(tiers, index) {
  const tier = tiers[index];
  const conditions = {};
  if (tier.threshold !== undefined && tier.threshold !== null && parseDecimal(tier.threshold).value > 0n) {
    conditions.min_total_input_tokens = numberString(tier.threshold);
  }
  const nextTier = tiers.slice(index + 1).find((candidate) => (
    candidate.threshold !== undefined && candidate.threshold !== null
  ));
  if (nextTier) {
    conditions.max_total_input_tokens = subtractDecimal(nextTier.threshold, "1");
  }
  return Object.keys(conditions).length > 0 ? { conditions } : {};
}

export function priceCardsFromOpenRouterModels(data, options = {}) {
  const retrievedAt = options.retrievedAt || options.retrieved_at || `${data.updated_at || "1970-01-01"}T00:00:00Z`;
  const sourceUrl = options.sourceUrl || options.source_url || "https://openrouter.ai/api/v1/models";
  const provider = options.provider || "openrouter";
  return (data.data || []).flatMap((model) => {
    if (!model || typeof model !== "object") {
      return [];
    }
    const modelId = model.id || model.canonical_slug;
    if (!modelId) {
      return [];
    }
    const tiers = openRouterPricingTiers(model.pricing);
    const components = [];
    tiers.forEach((tier, index) => {
      const tokenConditions = openRouterTierConditions(tiers, index);
      addPriceComponent(components, "input_uncached_tokens", "token", tier.prompt, "1", tokenConditions);
      addPriceComponent(components, "output_text_tokens", "token", tier.completion, "1", tokenConditions);
      addPriceComponent(components, "input_cache_read_tokens", "token", tier.input_cache_read, "1", tokenConditions);
      addPriceComponent(components, "input_cache_write_tokens", "token", tier.input_cache_write, "1", tokenConditions);
      addPriceComponent(components, "output_reasoning_tokens", "token", tier.internal_reasoning, "1", tokenConditions);
      if (index === 0) {
        addPriceComponent(components, "input_image_units", "image", tier.image);
        addPriceComponent(components, "request_units", "request", tier.request);
        addPriceComponent(components, "web_search_units", "search", tier.web_search);
      }
    });
    if (components.length === 0) return [];
    const aliases = [model.canonical_slug, model.name].filter((alias) => alias && alias !== modelId);
    const card = {
      schema_version: "0.1",
      id: `${provider}:${modelId}:openrouter-models`,
      provider,
      model: modelId,
      aliases,
      components,
      source: {
        name: "openrouter",
        url: sourceUrl,
        retrieved_at: retrievedAt
      }
    };
    if (model.expiration_date) {
      card.effective = { to: model.expiration_date };
    }
    return [card];
  });
}

function sourceInfo(data, defaultName, defaultUrl, options = {}) {
  const source = data && typeof data.source === "object" && data.source !== null ? data.source : {};
  const retrievedAt = options.retrievedAt || options.retrieved_at || source.retrieved_at || source.retrievedAt || data.retrieved_at || data.retrievedAt || `${data.updated_at || "1970-01-01"}T00:00:00Z`;
  const info = {
    name: options.sourceName || options.source_name || source.name || defaultName,
    url: options.sourceUrl || options.source_url || source.url || defaultUrl,
    retrieved_at: retrievedAt
  };
  if (source.version) info.version = source.version;
  if (source.license) info.license = source.license;
  return info;
}

function componentAmount(entry, keys) {
  const prices = entry.prices && typeof entry.prices === "object" ? entry.prices : {};
  const pricing = entry.pricing && typeof entry.pricing === "object" ? entry.pricing : {};
  for (const key of keys) {
    if (hasOwn(entry, key)) return entry[key];
    if (hasOwn(prices, key)) return prices[key];
    if (hasOwn(pricing, key)) return pricing[key];
  }
  return undefined;
}

function canonicalPriceCards(rawCards) {
  return Array.isArray(rawCards) ? rawCards.filter((card) => card && typeof card === "object") : [];
}

export function priceCardsFromUserPricing(data, options = {}) {
  if (Array.isArray(data)) {
    return canonicalPriceCards(data);
  }
  if (!data || typeof data !== "object") {
    return [];
  }
  if (data.price_cards) {
    return canonicalPriceCards(data.price_cards);
  }
  if (data.priceCards) {
    return canonicalPriceCards(data.priceCards);
  }

  const source = sourceInfo(data, "user-pricing", "file://user-pricing", options);
  const providerDefault = data.provider || options.provider || "user";
  const surfaceDefault = data.surface || options.surface;
  const serviceTierDefault = data.service_tier || data.serviceTier;
  const regionDefault = data.region;
  const perDefault = numberString(data.per || "1000000");
  return (data.models || []).flatMap((entry) => {
    if (!entry || typeof entry !== "object") return [];
    if (entry.components && entry.provider && (entry.model || entry.id)) {
      return [{
        ...entry,
        schema_version: entry.schema_version || "0.1",
        model: entry.model || entry.id,
        source: entry.source || source
      }];
    }

    const model = entry.model || entry.id;
    if (!model) return [];
    const provider = entry.provider || providerDefault;
    const per = numberString(entry.per || perDefault);
    const components = [];
    addPriceComponent(components, "input_uncached_tokens", "token", componentAmount(entry, ["input", "input_uncached", "input_uncached_tokens"]), per);
    addPriceComponent(components, "input_cache_read_tokens", "token", componentAmount(entry, ["cached_input", "input_cached", "cache_read", "input_cache_read"]), per);
    addPriceComponent(components, "input_cache_write_tokens", "token", componentAmount(entry, ["cache_write", "input_cache_write"]), per);
    addPriceComponent(components, "input_cache_write_1h_tokens", "token", componentAmount(entry, ["cache_write_1h", "input_cache_write_1h"]), per);
    addPriceComponent(components, "output_text_tokens", "token", componentAmount(entry, ["output", "completion", "output_text"]), per);
    addPriceComponent(components, "output_reasoning_tokens", "token", componentAmount(entry, ["reasoning", "thinking", "output_reasoning"]), per);
    addPriceComponent(components, "request_units", "request", componentAmount(entry, ["request", "per_request"]), "1");
    addPriceComponent(components, "web_search_units", "search", componentAmount(entry, ["web_search"]), "1");
    if (components.length === 0) return [];

    const card = {
      schema_version: "0.1",
      id: entry.price_card_id || entry.priceCardId || `${provider}:${model}:user-pricing`,
      provider,
      model,
      aliases: entry.aliases || [],
      components,
      source
    };
    const surface = entry.surface || surfaceDefault;
    if (surface) card.surface = surface;
    const serviceTier = entry.service_tier || entry.serviceTier || serviceTierDefault;
    if (serviceTier) card.service_tier = serviceTier;
    const region = entry.region || regionDefault;
    if (region) card.region = region;
    if (entry.effective && typeof entry.effective === "object") card.effective = entry.effective;
    return [card];
  });
}

function heliconeEndpointItems(data) {
  const endpoints = data.endpoints && typeof data.endpoints === "object" ? data.endpoints : data;
  if (Array.isArray(endpoints)) {
    return endpoints.filter((entry) => entry && typeof entry === "object");
  }
  if (endpoints && typeof endpoints === "object") {
    return Object.values(endpoints).filter((entry) => entry && typeof entry === "object");
  }
  return [];
}

function heliconePricingTiers(pricing) {
  const tiers = Array.isArray(pricing) ? pricing : [pricing];
  return tiers
    .filter((tier) => tier && typeof tier === "object")
    .sort((left, right) => Number(left.threshold || 0) - Number(right.threshold || 0));
}

function heliconeAddModalityComponents(components, tier, modality, conditions) {
  const pricing = tier[modality];
  if (!pricing || typeof pricing !== "object") return;
  const names = {
    image: ["input_image_tokens", "output_image_tokens"],
    audio: ["input_audio_tokens", "output_audio_tokens"],
    video: ["input_video_tokens", "output_video_tokens"]
  };
  if (!names[modality]) return;
  const [inputComponent, outputComponent] = names[modality];
  addPriceComponent(components, inputComponent, "token", pricing.input, "1", conditions);
  addPriceComponent(components, outputComponent, "token", pricing.output, "1", conditions);
}

export function priceCardsFromHelicone(data, options = {}) {
  const source = sourceInfo(data, "helicone", "https://github.com/Helicone/helicone/tree/main/packages/cost", options);
  return heliconeEndpointItems(data).flatMap((endpoint) => {
    const model = endpoint.providerModelId;
    const provider = endpoint.provider || options.provider;
    if (!model || !provider) return [];
    const tiers = heliconePricingTiers(endpoint.pricing);
    const components = [];
    tiers.forEach((tier, index) => {
      const conditions = thresholdTierConditions(tiers, index);
      const inputPrice = tier.input;
      addPriceComponent(components, "input_uncached_tokens", "token", inputPrice, "1", conditions);
      addPriceComponent(components, "output_text_tokens", "token", tier.output, "1", conditions);
      const cacheMultipliers = tier.cacheMultipliers && typeof tier.cacheMultipliers === "object" ? tier.cacheMultipliers : {};
      if (inputPrice !== undefined && inputPrice !== null) {
        if (cacheMultipliers.cachedInput !== undefined && cacheMultipliers.cachedInput !== null) {
          addPriceComponent(components, "input_cache_read_tokens", "token", multiplyDecimal(inputPrice, cacheMultipliers.cachedInput), "1", conditions);
        }
        if (cacheMultipliers.write5m !== undefined && cacheMultipliers.write5m !== null) {
          addPriceComponent(components, "input_cache_write_tokens", "token", multiplyDecimal(inputPrice, cacheMultipliers.write5m), "1", conditions);
        }
        if (cacheMultipliers.write1h !== undefined && cacheMultipliers.write1h !== null) {
          addPriceComponent(components, "input_cache_write_1h_tokens", "token", multiplyDecimal(inputPrice, cacheMultipliers.write1h), "1", conditions);
        }
      }
      addPriceComponent(components, "output_reasoning_tokens", "token", tier.thinking, "1", conditions);
      if (index === 0) {
        addPriceComponent(components, "request_units", "request", tier.request, "1");
        addPriceComponent(components, "web_search_units", "search", tier.web_search, "1");
      }
      ["image", "audio", "video"].forEach((modality) => heliconeAddModalityComponents(components, tier, modality, conditions));
    });
    if (components.length === 0) return [];
    return [{
      schema_version: "0.1",
      id: `${provider}:${model}:helicone`,
      provider,
      model,
      aliases: (endpoint.providerModelIdAliases || []).filter((alias) => alias && alias !== model),
      components,
      source,
      metadata: {
        author: endpoint.author,
        context_length: endpoint.contextLength,
        max_completion_tokens: endpoint.maxCompletionTokens,
        ptb_enabled: endpoint.ptbEnabled
      }
    }];
  });
}

export function fromResponse(response, options) {
  const mode = options.mode || "compatibility";
  let usageLedger;
  try {
    usageLedger = extractUsageLedger(response, options);
  } catch (error) {
    if (mode === "strict") {
      throw error;
    }
    return unsupportedSurfaceLedger(response, options);
  }
  return calculateCost({
    usageLedger,
    priceCards: options.priceCards || [],
    discountPolicies: options.discountPolicies || [],
    mode,
    staleAfterDays: options.staleAfterDays,
    stale_after_days: options.stale_after_days,
    providerReportedCost: options.providerReportedCost,
    provider_reported_cost: options.provider_reported_cost,
    providerReportedCostMode: options.providerReportedCostMode,
    provider_reported_cost_mode: options.provider_reported_cost_mode,
    priceSourcePriority: options.priceSourcePriority,
    price_source_priority: options.price_source_priority,
    debugTrace: options.debugTrace,
    debug_trace: options.debug_trace
  });
}

export function fromLangChainMessage(message, options) {
  return fromResponse(message, {
    ...options,
    adapter: "langchain.chat_message"
  });
}

export function fromVercelAISDKResult(result, options) {
  return fromResponse(result, {
    ...options,
    adapter: "vercel_ai_sdk.generate_text"
  });
}

export function fromLlamaIndexTokenCounter(counter, options) {
  return fromResponse(counter, {
    ...options,
    adapter: "llamaindex.token_counter"
  });
}

export function createRunCostVercelMiddleware(options = {}) {
  const ledgers = [];
  const onCostLedger = options.onCostLedger;
  const attachCostLedger = options.attachCostLedger !== false;
  const costOptions = { ...options };
  delete costOptions.onCostLedger;
  delete costOptions.attachCostLedger;

  return {
    ledgers,
    get latest() {
      return ledgers.length > 0 ? ledgers[ledgers.length - 1] : null;
    },
    async wrapGenerate({ doGenerate, params, model }) {
      const result = await doGenerate();
      const ledger = fromVercelAISDKResult(result, costOptions);
      ledgers.push(ledger);
      if (typeof onCostLedger === "function") {
        onCostLedger(ledger, { result, params, model });
      }
      if (!attachCostLedger || result == null || typeof result !== "object") {
        return result;
      }
      return {
        ...result,
        runCost: ledger
      };
    }
  };
}
