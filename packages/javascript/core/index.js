import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const MONEY_PRECISION = 18n;
const BILLING_WEEKDAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday"
];
const BILLING_WEEKDAY_INDEX = new Map(BILLING_WEEKDAYS.map((day, index) => [day, index]));
const BILLING_TIMEZONE_FORMATTERS = new Map();
const RFC3339_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const RFC3339_DATE_TIME_PATTERN = /^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$/;
const COMPONENT_ORDER_NAMES = [
  "input_uncached_tokens",
  "input_cache_read_tokens",
  "input_cache_write_tokens",
  "input_cache_write_1h_tokens",
  "input_image_units",
  "input_audio_tokens",
  "input_image_tokens",
  "input_video_tokens",
  "output_text_tokens",
  "output_reasoning_tokens",
  "output_audio_tokens",
  "output_image_tokens",
  "output_video_tokens",
  "embedding_tokens",
  "request_units",
  "web_search_units",
  "x_search_units",
  "file_search_units",
  "code_interpreter_session_units",
  "code_interpreter_call_units",
  "attachment_search_units",
  "computer_use_action_units",
  "tool_call_units",
  "tool_execution_seconds",
  "rerank_search_units",
  "image_generation_units",
  "video_generation_units",
  "audio_generation_units",
  "audio_generation_characters",
  "transcription_seconds",
  "endpoint_runtime_seconds",
  "endpoint_instance_hours",
  "storage_gb_days",
  "custom_units"
];
const COMPONENT_ORDER = new Map(COMPONENT_ORDER_NAMES.map((name, index) => [name, index]));
const TOOL_OR_FEATURE_COMPONENTS = new Set([
  "web_search_units",
  "x_search_units",
  "file_search_units",
  "code_interpreter_session_units",
  "code_interpreter_call_units",
  "attachment_search_units",
  "computer_use_action_units",
  "tool_call_units",
  "tool_execution_seconds",
  "rerank_search_units",
  "image_generation_units",
  "video_generation_units",
  "audio_generation_units",
  "audio_generation_characters",
  "transcription_seconds",
  "endpoint_runtime_seconds",
  "storage_gb_days"
]);
export const DEFAULT_EXTERNAL_PRICE_SOURCES = Object.freeze(["genai-prices", "models.dev", "litellm"]);
export const OPENROUTER_EXTERNAL_PRICE_SOURCES = Object.freeze(["openrouter", ...DEFAULT_EXTERNAL_PRICE_SOURCES]);
export const DEFAULT_PRICE_CACHE_MAX_AGE_SECONDS = 24 * 60 * 60;
export const EXTERNAL_PRICE_SOURCE_URLS = Object.freeze({
  "genai-prices": "https://raw.githubusercontent.com/pydantic/genai-prices/main/prices/data_slim.json",
  "models.dev": "https://models.dev/api.json",
  litellm: "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
  openrouter: "https://openrouter.ai/api/v1/models"
});

function normalizeDecimalString(value) {
  if (value === null || value === undefined) {
    return "0";
  }
  if (typeof value === "number" && !Number.isFinite(value)) {
    throw new Error(`invalid decimal: ${value}`);
  }
  const text = String(value).trim();
  if (text === "") {
    return "0";
  }
  if (!/[eE]/.test(text)) {
    return text.startsWith("+") ? text.slice(1) : text;
  }

  const match = text.match(/^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))[eE]([+-]?\d+)$/);
  if (!match) {
    throw new Error(`invalid decimal: ${value}`);
  }
  const [, rawSign, rawWhole, rawFrac, rawLeadingFrac, rawExponent] = match;
  const whole = rawWhole || "0";
  const frac = rawFrac ?? rawLeadingFrac ?? "";
  const rawDigits = `${whole}${frac}`;
  const leadingZeros = rawDigits.match(/^0*/)[0].length;
  const digits = rawDigits.slice(leadingZeros) || "0";
  if (digits === "0") {
    return "0";
  }
  const decimalIndex = whole.length + Number.parseInt(rawExponent, 10) - leadingZeros;
  let normalizedWhole;
  let normalizedFrac;
  if (decimalIndex <= 0) {
    normalizedWhole = "0";
    normalizedFrac = `${"0".repeat(-decimalIndex)}${digits}`;
  } else if (decimalIndex >= digits.length) {
    normalizedWhole = `${digits}${"0".repeat(decimalIndex - digits.length)}`;
    normalizedFrac = "";
  } else {
    normalizedWhole = digits.slice(0, decimalIndex);
    normalizedFrac = digits.slice(decimalIndex);
  }
  normalizedWhole = normalizedWhole.replace(/^0+(?=\d)/, "") || "0";
  normalizedFrac = normalizedFrac.replace(/0+$/, "");
  const sign = rawSign === "-" ? "-" : "";
  return `${sign}${normalizedWhole}${normalizedFrac ? `.${normalizedFrac}` : ""}`;
}

function parseDecimal(value) {
  const text = normalizeDecimalString(value);
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

function canonicalDecimal(value) {
  const parsed = parseDecimal(value);
  return formatDecimal(parsed.value, parsed.scale);
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

function compareDecimal(left, right) {
  const difference = parseDecimal(subtractDecimal(left, right)).value;
  return difference < 0n ? -1 : difference > 0n ? 1 : 0;
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

function dateOnlyValue(value) {
  if (value === undefined || value === null) return null;
  const text = String(value);
  if (!RFC3339_DATE_PATTERN.test(text)) return null;
  const parsed = Date.parse(`${text}T00:00:00Z`);
  if (Number.isNaN(parsed)) return null;
  const normalized = new Date(parsed).toISOString().slice(0, 10);
  return normalized === text ? { kind: "date", text, value: parsed } : null;
}

function dateValue(value) {
  const parsed = dateOnlyValue(datePart(value));
  return parsed ? parsed.value : null;
}

function usageContext(usageLedger) {
  return usageLedger.context || {};
}

function dateTimeValue(value) {
  if (value === undefined || value === null) return null;
  const text = String(value);
  if (!RFC3339_DATE_TIME_PATTERN.test(text)) return null;
  const normalizedText = text.replace(/[Tt]/, "T").replace(/[Zz]$/, "Z");
  const parsed = Date.parse(normalizedText);
  return Number.isNaN(parsed) ? null : new Date(parsed);
}

function pricedAtValue(value) {
  const date = dateOnlyValue(value);
  if (date) return date;
  const dateTime = dateTimeValue(value);
  if (dateTime) return { kind: "datetime", value: dateTime.getTime() };
  if (value === undefined || value === null || value === "") return null;
  return { kind: "invalid" };
}

function effectiveBoundary(value) {
  if (value === undefined || value === null || value === "") return null;
  const date = dateOnlyValue(value);
  if (date) return date;
  const dateTime = dateTimeValue(value);
  if (dateTime) return { kind: "datetime", value: dateTime.getTime() };
  return { kind: "invalid" };
}

function unixSecondsPricedAt(value) {
  if (value === undefined || value === null) return null;
  const seconds = Number(value);
  if (!Number.isFinite(seconds)) return null;
  const date = new Date(Math.trunc(seconds) * 1000);
  if (Number.isNaN(date.getTime())) return null;
  try {
    return date.toISOString().replace(".000Z", "Z");
  } catch {
    return null;
  }
}

function cardPricingPeriod(card) {
  const value = card.pricing_period || card.pricingPeriod;
  return value ? String(value) : null;
}

function cardBillingSchedule(card) {
  const schedule = card.billing_schedule || card.billingSchedule || {};
  return schedule && typeof schedule === "object" ? schedule : {};
}

function normalizeBillingSchedule(schedule) {
  if (!schedule || typeof schedule !== "object") return null;
  const normalized = {};
  if (schedule.timezone !== undefined) normalized.timezone = schedule.timezone;
  const defaultPeriod = schedule.default_period ?? schedule.defaultPeriod;
  if (defaultPeriod !== undefined) normalized.default_period = defaultPeriod;
  const boundaryPolicy = schedule.boundary_policy ?? schedule.boundaryPolicy;
  if (boundaryPolicy !== undefined) normalized.boundary_policy = boundaryPolicy;
  if (Array.isArray(schedule.windows)) {
    normalized.windows = schedule.windows.map((window) => {
      if (!window || typeof window !== "object") return window;
      const normalizedWindow = {};
      if (window.period !== undefined) normalizedWindow.period = window.period;
      if (window.start !== undefined) normalizedWindow.start = window.start;
      if (window.end !== undefined) normalizedWindow.end = window.end;
      if (window.days_of_week !== undefined && window.daysOfWeek !== undefined) {
        // Keep the ambiguity observable so schedule evaluation fails closed.
        normalizedWindow.days_of_week = [];
      } else if (window.days_of_week !== undefined) {
        normalizedWindow.days_of_week = window.days_of_week;
      } else if (window.daysOfWeek !== undefined) {
        normalizedWindow.days_of_week = window.daysOfWeek;
      }
      return normalizedWindow;
    });
  } else if ("windows" in schedule) {
    normalized.windows = schedule.windows;
  }
  return normalized;
}

function timeSeconds(value) {
  if (typeof value !== "string") return null;
  const parts = value.split(":");
  if (![2, 3].includes(parts.length)) return null;
  const [hourText, minuteText, secondText = "0"] = parts;
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = Number(secondText);
  if (
    !Number.isInteger(hour) ||
    !Number.isInteger(minute) ||
    !Number.isInteger(second) ||
    hour < 0 ||
    hour > 23 ||
    minute < 0 ||
    minute > 59 ||
    second < 0 ||
    second > 59
  ) {
    return null;
  }
  return hour * 3600 + minute * 60 + second;
}

function timeInWindow(current, start, end) {
  if (start <= end) return current >= start && current < end;
  return current >= start || current < end;
}

function billingTimezoneLabel(timezone) {
  if (typeof timezone === "string") return timezone;
  if (timezone === null) return "null";
  return String(timezone);
}

function billingTimezoneFormatter(timezone) {
  if (BILLING_TIMEZONE_FORMATTERS.has(timezone)) {
    return BILLING_TIMEZONE_FORMATTERS.get(timezone);
  }
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    weekday: "long",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23"
  });
  BILLING_TIMEZONE_FORMATTERS.set(timezone, formatter);
  return formatter;
}

function billingScheduleTimezone(schedule) {
  const timezone = schedule.timezone === undefined ? "UTC" : schedule.timezone;
  if (typeof timezone !== "string" || timezone === "") {
    return { unsupported_timezone: billingTimezoneLabel(timezone) };
  }
  try {
    // Intl validates IANA zone names in both Node and browser builds. Keeping
    // this dynamic avoids a provider-specific allowlist while still rejecting
    // a misspelled or unavailable zone before pricing is attempted.
    billingTimezoneFormatter(timezone);
  } catch {
    return { unsupported_timezone: billingTimezoneLabel(timezone) };
  }
  return { timezone };
}

function billingWindowDays(window) {
  const hasCanonical = hasOwn(window, "days_of_week");
  const hasAlias = hasOwn(window, "daysOfWeek");
  if (hasCanonical && hasAlias) {
    return { unsupported_schedule: "days_of_week" };
  }
  if (!hasCanonical && !hasAlias) return { days: null };
  const rawDays = hasCanonical ? window.days_of_week : window.daysOfWeek;
  if (!Array.isArray(rawDays) || rawDays.length === 0) {
    return { unsupported_schedule: "days_of_week" };
  }
  const days = new Set();
  for (const day of rawDays) {
    if (typeof day !== "string" || !BILLING_WEEKDAY_INDEX.has(day) || days.has(day)) {
      return { unsupported_schedule: "days_of_week" };
    }
    days.add(day);
  }
  return { days };
}

function billingScheduleDefinition(schedule) {
  const timezoneResult = billingScheduleTimezone(schedule);
  if (timezoneResult.unsupported_timezone) return timezoneResult;
  const boundaryPolicy = schedule.boundary_policy || schedule.boundaryPolicy || "start_inclusive_end_exclusive";
  if (boundaryPolicy !== "start_inclusive_end_exclusive") {
    return { unsupported_schedule: "boundary_policy" };
  }
  if (!Array.isArray(schedule.windows)) {
    return { unsupported_schedule: "windows" };
  }
  const windows = [];
  for (const window of schedule.windows) {
    if (!window || typeof window !== "object" || Array.isArray(window)) {
      return { unsupported_schedule: "window" };
    }
    const start = timeSeconds(window.start);
    const end = timeSeconds(window.end);
    if (start === null || end === null || !window.period) {
      return { unsupported_schedule: "window" };
    }
    const days = billingWindowDays(window);
    if (days.unsupported_schedule) return days;
    windows.push({ window, start, end, days: days.days });
  }
  return { timezone: timezoneResult.timezone, windows };
}

function billingLocalParts(pricedAt, timezone) {
  try {
    const parts = {};
    for (const part of billingTimezoneFormatter(timezone).formatToParts(pricedAt)) {
      if (["weekday", "hour", "minute", "second"].includes(part.type)) {
        parts[part.type] = part.value;
      }
    }
    const weekday = BILLING_WEEKDAY_INDEX.get(String(parts.weekday || "").toLowerCase());
    const hour = Number(parts.hour);
    const minute = Number(parts.minute);
    const second = Number(parts.second);
    if (
      weekday === undefined ||
      !Number.isInteger(hour) ||
      !Number.isInteger(minute) ||
      !Number.isInteger(second) ||
      hour < 0 ||
      hour > 23 ||
      minute < 0 ||
      minute > 59 ||
      second < 0 ||
      second > 59
    ) {
      return null;
    }
    return {
      weekday,
      seconds: hour * 3600 + minute * 60 + second
    };
  } catch {
    return null;
  }
}

function billingWindowMatches(current, start, end, days) {
  if (!timeInWindow(current.seconds, start, end)) return false;
  if (!days) return true;
  const startDay = current.seconds >= start
    ? current.weekday
    : (current.weekday + BILLING_WEEKDAYS.length - 1) % BILLING_WEEKDAYS.length;
  return days.has(BILLING_WEEKDAYS[startDay]);
}

function pricingPeriodFromSchedule(schedule, pricedAt) {
  const definition = billingScheduleDefinition(schedule);
  if (definition.unsupported_timezone || definition.unsupported_schedule) return definition;
  const current = billingLocalParts(pricedAt, definition.timezone);
  if (!current) return { unsupported_schedule: "timezone" };
  for (const { window, start, end, days } of definition.windows) {
    if (billingWindowMatches(current, start, end, days)) {
      return {
        pricing_period: String(window.period),
        period_selection: "derived_from_priced_at",
        pricing_window: `${window.start}-${window.end}`,
        pricing_timezone: definition.timezone
      };
    }
  }
  const defaultPeriod = schedule.default_period || schedule.defaultPeriod;
  if (defaultPeriod) {
    return {
      pricing_period: String(defaultPeriod),
      period_selection: "derived_from_priced_at",
      pricing_window: "default",
      pricing_timezone: definition.timezone
    };
  }
  return {};
}

function pricingPeriodSelection(usageLedger, card) {
  const context = usageContext(usageLedger);
  const explicit = context.pricing_period || context.pricingPeriod;
  if (explicit) {
    return { pricing_period: String(explicit), period_selection: "explicit_context" };
  }
  const schedule = cardBillingSchedule(card);
  if (Object.keys(schedule).length === 0) return {};
  const pricedAt = dateTimeValue(context.priced_at || context.pricedAt);
  if (!pricedAt) return {};
  return pricingPeriodFromSchedule(schedule, pricedAt);
}

function cardPricingPeriodMatches(usageLedger, card) {
  const period = cardPricingPeriod(card);
  if (!period) return true;
  return pricingPeriodSelection(usageLedger, card).pricing_period === period;
}

function cardPeriodRank(usageLedger, card) {
  const period = cardPricingPeriod(card);
  if (!period) return 0;
  return pricingPeriodSelection(usageLedger, card).pricing_period === period ? 1 : 0;
}

function pricingPeriodsForCards(cards) {
  return [...new Set(cards.map(cardPricingPeriod).filter(Boolean))].sort();
}

function requestedPricingPeriodForCards(usageLedger, cards) {
  const context = usageContext(usageLedger);
  const explicit = context.pricing_period || context.pricingPeriod;
  if (explicit) return String(explicit);
  for (const card of cards) {
    const selection = pricingPeriodSelection(usageLedger, card);
    if (selection.pricing_period) return String(selection.pricing_period);
  }
  return null;
}

function unsupportedBillingScheduleReason(usageLedger, cards) {
  const context = usageContext(usageLedger);
  if (context.pricing_period || context.pricingPeriod) return null;
  for (const card of cards) {
    const schedule = cardBillingSchedule(card);
    if (Object.keys(schedule).length === 0) continue;
    const definition = billingScheduleDefinition(schedule);
    if (definition.unsupported_timezone) return String(definition.unsupported_timezone);
    if (definition.unsupported_schedule) return String(definition.unsupported_schedule);
    if (!dateTimeValue(context.priced_at || context.pricedAt)) continue;
    const selection = pricingPeriodSelection(usageLedger, card);
    if (selection.unsupported_timezone) return String(selection.unsupported_timezone);
    if (selection.unsupported_schedule) return String(selection.unsupported_schedule);
  }
  return null;
}

function compareText(left, right) {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

function compareTuple(left, right) {
  for (let index = 0; index < left.length; index += 1) {
    const compared = compareText(String(left[index] ?? ""), String(right[index] ?? ""));
    if (compared !== 0) return compared;
  }
  return 0;
}

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function componentSortKey(component) {
  const name = String(component.name || "");
  return [
    String(COMPONENT_ORDER.has(name) ? COMPONENT_ORDER.get(name) : COMPONENT_ORDER.size).padStart(4, "0"),
    name,
    component.unit || "",
    component.unit_price || "",
    component.price_card_id || "",
    component.quantity || "",
    component.cost || ""
  ];
}

function sourceSortKey(source) {
  return [
    source.name || "",
    source.url || "",
    source.retrieved_at || "",
    source.version || ""
  ];
}

function discountSortKey(discount) {
  return [
    discount.component || "",
    discount.policy_id || "",
    discount.amount || ""
  ];
}

function warningSortKey(warning) {
  return [
    warning.code || "",
    warning.path || "",
    warning.message || "",
    stableStringify(warning.metadata || {})
  ];
}

function orderedCostComponents(components) {
  return [...components].sort((left, right) => compareTuple(componentSortKey(left), componentSortKey(right)));
}

function orderedPriceSources(sources) {
  return [...sources].sort((left, right) => compareTuple(sourceSortKey(left), sourceSortKey(right)));
}

function orderedAppliedDiscounts(discounts) {
  return [...discounts].sort((left, right) => compareTuple(discountSortKey(left), discountSortKey(right)));
}

function orderedWarnings(warnings) {
  return [...warnings].sort((left, right) => compareTuple(warningSortKey(left), warningSortKey(right)));
}

function cardIdentityMatches(usageLedger, card) {
  const model = billedModel(usageLedger);
  const modelMatches = card.model === model || (card.aliases || []).includes(model);
  const providerMatches = card.provider === usageLedger.provider;
  const surfaceMatches = !card.surface || card.surface === usageLedger.surface;
  return modelMatches && providerMatches && surfaceMatches;
}

function cardModelSurfaceMatches(usageLedger, card) {
  const model = billedModel(usageLedger);
  const modelMatches = card.model === model || (card.aliases || []).includes(model);
  const surfaceMatches = !card.surface || card.surface === usageLedger.surface;
  return modelMatches && surfaceMatches;
}

function effectiveMatches(card, pricedAt) {
  const effective = card.effective || {};
  if (!effective || typeof effective !== "object" || Array.isArray(effective)) return false;
  const from = effectiveBoundary(effective.from);
  const to = effectiveBoundary(effective.to);
  if (from?.kind === "invalid" || to?.kind === "invalid") return false;
  const usage = pricedAtValue(pricedAt);
  if (!usage) {
    return from?.kind !== "datetime" && to?.kind !== "datetime";
  }
  if (usage.kind === "invalid") return false;
  if (usage.kind === "date" && (from?.kind === "datetime" || to?.kind === "datetime")) {
    return false;
  }
  const usageValue = usage.value;
  if (from && usageValue < from.value) return false;
  if (to) {
    const toExclusive = to.kind === "date" ? to.value + 86400000 : to.value;
    if (usageValue >= toExclusive) return false;
  }
  return true;
}

function cardContextMatches(usageLedger, card) {
  return cardContextExceptPeriodMatches(usageLedger, card) && cardPricingPeriodMatches(usageLedger, card);
}

function cardContextExceptPeriodMatches(usageLedger, card) {
  const context = usageContext(usageLedger);
  const requestedServiceTier = context.service_tier || "standard";
  const pricedAt = context.priced_at ?? context.pricedAt;
  if (card.service_tier && card.service_tier !== requestedServiceTier) {
    return false;
  }
  if (context.region && card.region && card.region !== context.region) {
    return false;
  }
  return effectiveMatches(card, pricedAt);
}

function cardScore(usageLedger, card) {
  const context = usageContext(usageLedger);
  const requestedServiceTier = context.service_tier || "standard";
  let score = 0;
  if (card.surface === usageLedger.surface) score += 8;
  if (card.service_tier === requestedServiceTier) score += 4;
  if (context.region && card.region === context.region) score += 2;
  if (card.effective) score += 1;
  if (cardPricingPeriod(card)) score += 4;
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

function matchingCardsExact(usageLedger, priceCards, priceSourcePriority = []) {
  const periodContextCards = priceCards.filter((card) => (
    cardIdentityMatches(usageLedger, card) &&
    cardPricingPeriod(card) &&
    cardContextExceptPeriodMatches(usageLedger, card)
  ));
  const scored = [];
  for (let index = 0; index < priceCards.length; index += 1) {
    const card = priceCards[index];
    if (!cardIdentityMatches(usageLedger, card) || !cardContextMatches(usageLedger, card)) continue;
    scored.push({
      card,
      index,
      periodRank: cardPeriodRank(usageLedger, card),
      score: cardScore(usageLedger, card) + sourcePriorityScore(card, priceSourcePriority)
    });
  }
  if (periodContextCards.length > 0 && scored.length > 0 && !scored.some((item) => item.periodRank === 1)) {
    const unsupportedReason = unsupportedBillingScheduleReason(usageLedger, periodContextCards);
    const requestedPeriod = requestedPricingPeriodForCards(usageLedger, periodContextCards);
    if (unsupportedReason || requestedPeriod) return [];
  }
  return scored
    .sort((a, b) => (
      b.periodRank - a.periodRank ||
      b.score - a.score ||
      compareText(String((a.card.source || {}).name || ""), String((b.card.source || {}).name || "")) ||
      compareText(String(a.card.id || ""), String(b.card.id || "")) ||
      a.index - b.index
    ))
    .map(({ card }) => card);
}

function matchingCards(usageLedger, priceCards, priceSourcePriority = []) {
  const exact = matchingCardsExact(usageLedger, priceCards, priceSourcePriority);
  const context = usageContext(usageLedger);
  if (usageLedger.provider !== "openai" || context.service_tier !== "fast") return exact;
  const exactFast = exact.filter((card) => card.service_tier === "fast");
  if (exactFast.length > 0) return exactFast;
  const fallbackUsageLedger = {
    ...usageLedger,
    context: { ...context, service_tier: "priority" }
  };
  return matchingCardsExact(fallbackUsageLedger, priceCards, priceSourcePriority)
    .filter((card) => card.service_tier === "priority");
}

function serviceTierFallbackMetadata(usageLedger, card) {
  const context = usageContext(usageLedger);
  if (usageLedger.provider === "openai" && context.service_tier === "fast" && card.service_tier === "priority") {
    return { requested: "fast", priced_as: "priority", fallback: true };
  }
  return undefined;
}

function priceLookupCacheKey(usageLedger, sourcePriority = []) {
  const context = usageContext(usageLedger);
  return JSON.stringify([
    usageLedger.provider || "",
    usageLedger.surface || "",
    billedModel(usageLedger),
    context.service_tier || "",
    context.region || "",
    context.pricing_period || context.pricingPeriod || "",
    context.priced_at || context.pricedAt || "",
    sourcePriority
  ]);
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

function authoritativeSourceCandidates(usageLedger, candidates, sourcePriority) {
  if (candidates.length === 0 || !sourcePriority || sourcePriority.length === 0) {
    return candidates;
  }
  const sourceName = (candidates[0].card.source || {}).name || "";
  if (!sourcePriority.includes(sourceName)) {
    return candidates;
  }
  const metadata = candidates[0].card.metadata || {};
  if (!metadata.official_snapshot || typeof metadata.official_snapshot !== "object") {
    return candidates;
  }
  const sourceCandidates = candidates.filter(({ card }) => ((card.source || {}).name || "") === sourceName);
  if (!sourceCandidates.some(({ priceComponent }) => priceComponent.conditions)) {
    return candidates;
  }
  if (sourceCandidates.some(({ priceComponent }) => conditionsMatch(usageLedger, priceComponent))) {
    return candidates;
  }
  return sourceCandidates;
}

function warningIdentityMetadata(usageLedger) {
  return {
    provider: usageLedger.provider,
    surface: usageLedger.surface,
    model: billedModel(usageLedger)
  };
}

function aliasInferredWarning(requestedModel, billedModelValue) {
  return {
    code: "alias_inferred",
    message: `Resolved model alias ${requestedModel} to billed model ${billedModelValue}.`,
    metadata: {
      requested_model: requestedModel,
      billed_model: billedModelValue
    }
  };
}

function unpricedComponentMetadata(usageLedger, component) {
  return {
    component: component.name,
    unit: component.unit,
    model: billedModel(usageLedger)
  };
}

function isToolOrFeatureComponent(componentName) {
  return TOOL_OR_FEATURE_COMPONENTS.has(componentName);
}

function unpricedComponentWarning(usageLedger, component) {
  if (isToolOrFeatureComponent(component.name)) {
    return {
      code: "tool_component_unpriced",
      message: `No price found for tool or feature component ${component.name} on model ${billedModel(usageLedger)}.`,
      metadata: unpricedComponentMetadata(usageLedger, component)
    };
  }
  return {
    code: "component_unpriced",
    message: `No price found for ${component.name} (${component.unit}).`,
    metadata: unpricedComponentMetadata(usageLedger, component)
  };
}

function longContextRuleMissingWarning(usageLedger, candidates, component) {
  if (candidates.length === 0 || !candidates.some(({ priceComponent }) => priceComponent.conditions)) {
    return null;
  }
  const totalInput = totalInputTokens(usageLedger);
  const totalInputFormatted = formatDecimal(totalInput.value, totalInput.scale);
  return {
    code: "long_context_rule_missing",
    message: `No long-context pricing rule matched ${component.name} at ${totalInputFormatted} input tokens.`,
    metadata: {
      component: component.name,
      unit: component.unit,
      total_input_tokens: totalInputFormatted
    }
  };
}

function sourceCapabilityUnsupported(card, componentName) {
  const metadata = card.metadata && typeof card.metadata === "object" ? card.metadata : {};
  const capabilities = metadata.source_capabilities && typeof metadata.source_capabilities === "object"
    ? metadata.source_capabilities
    : null;
  if (!capabilities) {
    return false;
  }
  const unsupported = capabilities.unsupported_components || capabilities.unsupportedComponents || [];
  return unsupported.includes(componentName);
}

function sourceCapabilityWarning(matchingCards, component) {
  for (const card of matchingCards) {
    if (sourceCapabilityUnsupported(card, component.name)) {
      const source = card.source && typeof card.source === "object" ? card.source : {};
      return {
        code: "source_capability_unsupported",
        message: `Price source ${source.name || card.id || "unknown"} explicitly does not price ${component.name}.`,
        metadata: {
          component: component.name,
          unit: component.unit,
          price_card_id: card.id,
          source: source.name
        }
      };
    }
  }
  return null;
}

function modelNameLooksGemini(value) {
  return String(value || "").toLowerCase().startsWith("gemini-") ||
    String(value || "").toLowerCase().startsWith("google/gemini-");
}

function modelNameLooksGeminiLiveTranslate(value) {
  return [
    "gemini-3.5-live-translate-preview",
    "google/gemini-3.5-live-translate-preview"
  ].includes(String(value || "").toLowerCase());
}

function modelNameLooksXAI(value) {
  const text = String(value || "").toLowerCase();
  return text.startsWith("grok-") || text.startsWith("xai/");
}

const OUTPUT_PRICE_FALLBACK_COMPONENTS = [
  "output_text_tokens",
  "output_audio_tokens",
  "output_image_tokens",
  "output_video_tokens"
];

function outputPriceFallbackComponentCandidates(usageLedger, preferred = []) {
  const candidates = [];
  for (const componentName of preferred) {
    if (
      OUTPUT_PRICE_FALLBACK_COMPONENTS.includes(componentName) &&
      !candidates.includes(componentName)
    ) {
      candidates.push(componentName);
    }
  }
  for (const component of usageLedger.components || []) {
    if (
      component.unit === "token" &&
      OUTPUT_PRICE_FALLBACK_COMPONENTS.includes(component.name) &&
      isPositiveDecimal(component.quantity || "0") &&
      !candidates.includes(component.name)
    ) {
      candidates.push(component.name);
    }
  }
  for (const componentName of OUTPUT_PRICE_FALLBACK_COMPONENTS) {
    if (!candidates.includes(componentName)) {
      candidates.push(componentName);
    }
  }
  return candidates;
}

function geminiThinkingPricedAsOutputApplies(usageLedger, card) {
  const provider = String(usageLedger.provider || card.provider || "").toLowerCase();
  const surface = String(usageLedger.surface || card.surface || "").toLowerCase();
  if (!["google", "vertex", "google-vertex"].includes(provider) && !surface.includes("gemini.")) {
    return false;
  }
  const modelNames = [
    billedModel(usageLedger),
    card.model,
    ...(card.aliases || [])
  ];
  return modelNames.some(modelNameLooksGemini);
}

function geminiThinkingOutputComponentCandidates(usageLedger, card) {
  const surface = String(usageLedger.surface || card.surface || "").toLowerCase();
  const modelNames = [
    billedModel(usageLedger),
    card.model,
    ...(card.aliases || [])
  ];
  const isLiveTranslate = surface === "google.gemini.live" &&
    modelNames.some(modelNameLooksGeminiLiveTranslate);
  const preferred = isLiveTranslate ? ["output_audio_tokens"] : [];
  return outputPriceFallbackComponentCandidates(usageLedger, preferred);
}

function geminiThinkingOutputComponentNames(usageLedger, candidateCards) {
  const componentNames = [];
  for (const card of candidateCards) {
    if (!geminiThinkingPricedAsOutputApplies(usageLedger, card)) {
      continue;
    }
    for (const componentName of geminiThinkingOutputComponentCandidates(usageLedger, card)) {
      if (!componentNames.includes(componentName)) {
        componentNames.push(componentName);
      }
    }
  }
  return componentNames;
}

function geminiThinkingPricedAsOutputMatches(usageLedger, candidateCards, component) {
  if (component.name !== "output_reasoning_tokens" || component.unit !== "token") {
    return [];
  }
  for (const outputComponentName of geminiThinkingOutputComponentNames(usageLedger, candidateCards)) {
    const outputComponent = {
      name: outputComponentName,
      unit: component.unit
    };
    const matches = findPriceComponents(usageLedger, candidateCards, outputComponent)
      .filter(({ card }) => geminiThinkingPricedAsOutputApplies(usageLedger, card))
      .filter(({ card }) => geminiThinkingOutputComponentCandidates(usageLedger, card).includes(outputComponentName))
      .filter(({ card }) => !sourceCapabilityUnsupported(card, "output_reasoning_tokens"))
      .map(({ card, priceComponent }) => ({
        card,
        priceComponent: {
          ...priceComponent,
          usage_component: "output_reasoning_tokens",
          notes: priceComponent.notes || "Gemini thinking tokens are priced at the output-token rate."
        },
        componentMetadata: {
          pricing_policy: "gemini_thinking_tokens_priced_as_output_tokens",
          priced_as_component: outputComponentName
        }
      }));
    if (matches.length > 0) {
      return matches;
    }
  }
  return [];
}

function xaiReasoningPricedAsOutputApplies(usageLedger, card) {
  const provider = String(usageLedger.provider || card.provider || "").toLowerCase();
  const surface = String(usageLedger.surface || card.surface || "").toLowerCase();
  if (provider !== "xai" && !surface.startsWith("xai.")) {
    return false;
  }
  const modelNames = [
    billedModel(usageLedger),
    card.model,
    ...(card.aliases || [])
  ];
  return modelNames.some(modelNameLooksXAI) || provider === "xai";
}

function xaiReasoningPricedAsOutputMatches(usageLedger, candidateCards, component) {
  if (component.name !== "output_reasoning_tokens" || component.unit !== "token") {
    return [];
  }
  const outputComponent = {
    name: "output_text_tokens",
    unit: component.unit
  };
  return findPriceComponents(usageLedger, candidateCards, outputComponent)
    .filter(({ card }) => xaiReasoningPricedAsOutputApplies(usageLedger, card))
    .filter(({ card }) => !sourceCapabilityUnsupported(card, "output_reasoning_tokens"))
    .map(({ card, priceComponent }) => ({
      card,
      priceComponent: {
        ...priceComponent,
        usage_component: "output_reasoning_tokens",
        notes: priceComponent.notes || "xAI reasoning tokens are priced at the output-token rate."
      },
      componentMetadata: {
        pricing_policy: "xai_reasoning_tokens_priced_as_output_tokens",
        priced_as_component: "output_text_tokens"
      }
    }));
}

function genericReasoningPricedAsOutputMatches(usageLedger, candidateCards, component) {
  if (component.name !== "output_reasoning_tokens" || component.unit !== "token") {
    return [];
  }
  for (const outputComponentName of outputPriceFallbackComponentCandidates(usageLedger)) {
    const outputComponent = {
      name: outputComponentName,
      unit: component.unit
    };
    const matches = findPriceComponents(usageLedger, candidateCards, outputComponent)
      .filter(({ card }) => !sourceCapabilityUnsupported(card, "output_reasoning_tokens"))
      .map(({ card, priceComponent }) => ({
        card,
        priceComponent: {
          ...priceComponent,
          usage_component: "output_reasoning_tokens",
          notes: priceComponent.notes || "Reasoning tokens are priced at the output-token rate by default."
        },
        componentMetadata: {
          pricing_policy: "reasoning_tokens_priced_as_output_tokens",
          priced_as_component: outputComponentName,
          fallback_reason: "no_separate_reasoning_price"
        }
      }));
    if (matches.length > 0) {
      return matches;
    }
  }
  return [];
}

function outputReasoningPricedAsOutputMatches(usageLedger, candidateCards, component) {
  const providerSpecificMatches = [
    ...geminiThinkingPricedAsOutputMatches(usageLedger, candidateCards, component),
    ...xaiReasoningPricedAsOutputMatches(usageLedger, candidateCards, component)
  ];
  if (providerSpecificMatches.length > 0) {
    return providerSpecificMatches;
  }
  return genericReasoningPricedAsOutputMatches(usageLedger, candidateCards, component);
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
      message: `No price card found for service tier ${context.service_tier}.`,
      metadata: {
        model: billedModel(usageLedger),
        service_tier: context.service_tier
      }
    };
  }
  const periodCards = identityCards.filter((card) => (
    cardPricingPeriod(card) &&
    cardContextExceptPeriodMatches(usageLedger, card)
  ));
  if (periodCards.length > 0) {
    const unsupportedReason = unsupportedBillingScheduleReason(usageLedger, periodCards);
    if (unsupportedReason) {
      return {
        code: "billing_schedule_unsupported",
        message: `Billing schedule ${unsupportedReason} is not supported.`,
        metadata: {
          ...warningIdentityMetadata(usageLedger),
          timezone: unsupportedReason
        }
      };
    }
    const requestedPeriod = requestedPricingPeriodForCards(usageLedger, periodCards);
    if (requestedPeriod) {
      return {
        code: "pricing_period_unsupported",
        message: `No price card found for pricing period ${requestedPeriod}.`,
        metadata: {
          ...warningIdentityMetadata(usageLedger),
          pricing_period: requestedPeriod
        }
      };
    }
    return {
      code: "pricing_period_required",
      message: "Pricing period is required for period-specific price cards.",
      metadata: {
        ...warningIdentityMetadata(usageLedger),
        pricing_periods: pricingPeriodsForCards(periodCards)
      }
    };
  }

  const pricedAt = context.priced_at ?? context.pricedAt;
  const pricedAtDate = datePart(pricedAt);
  if (
    pricedAtDate &&
    identityCards.length > 0 &&
    !identityCards.some((card) => effectiveMatches(card, pricedAt))
  ) {
    return {
      code: "historical_price_missing",
      message: `No price card effective for ${pricedAtDate}.`,
      metadata: {
        model: billedModel(usageLedger),
        priced_at: pricedAtDate
      }
    };
  }

  const model = billedModel(usageLedger);
  return {
    code: "price_not_found",
    message: `No price card matched provider, surface, model, and context for ${model}.`,
    metadata: warningIdentityMetadata(usageLedger)
  };
}

function hasPriceCardForUsage(usageLedger, priceCards) {
  return priceCards.some((card) => cardIdentityMatches(usageLedger, card));
}

function hasPriceCardForModelSurface(usageLedger, priceCards) {
  return priceCards.some((card) => cardModelSurfaceMatches(usageLedger, card));
}

export function compilePriceCatalog(priceCards) {
  if (priceCards && priceCards.__runcostCompiledCatalog === true) return priceCards;
  const cards = [...(priceCards || [])];
  const byProviderModel = new Map();
  const byModel = new Map();
  for (const card of cards) {
    const provider = String(card.provider || "");
    const names = [...new Set([card.model, ...(card.aliases || [])].filter(Boolean).map(String))];
    for (const name of names) {
      const providerKey = `${provider}\u0000${name}`;
      if (!byProviderModel.has(providerKey)) byProviderModel.set(providerKey, []);
      byProviderModel.get(providerKey).push(card);
      if (!byModel.has(name)) byModel.set(name, []);
      byModel.get(name).push(card);
    }
  }
  return Object.freeze({
    __runcostCompiledCatalog: true,
    priceCards: cards,
    byProviderModel,
    byModel
  });
}

function compiledIdentityCandidates(catalog, usageLedger) {
  return catalog.byProviderModel.get(`${usageLedger.provider || ""}\u0000${billedModel(usageLedger)}`) || [];
}

function compiledModelCandidates(catalog, usageLedger) {
  return catalog.byModel.get(billedModel(usageLedger)) || [];
}

function unknownProviderWarning(usageLedger) {
  return {
    code: "unknown_provider",
    message: `No price card found for provider ${usageLedger.provider}.`,
    metadata: warningIdentityMetadata(usageLedger)
  };
}

function unknownModelWarning(usageLedger) {
  const model = billedModel(usageLedger);
  return {
    code: "unknown_model",
    message: `No price card found for ${model}.`,
    metadata: warningIdentityMetadata(usageLedger)
  };
}

function usageMetadataFieldWarnings(usageLedger) {
  const metadata = usageLedger.metadata && typeof usageLedger.metadata === "object" ? usageLedger.metadata : {};
  const warnings = [];
  for (const field of metadata.ignored_usage_fields || []) {
    const fieldName = String(field);
    warnings.push({
      code: "usage_field_ignored",
      message: `Usage field ${fieldName} was not mapped to a cost component.`,
      path: fieldName,
      metadata: { field: fieldName }
    });
  }
  for (const field of metadata.missing_usage_fields || []) {
    const fieldName = String(field);
    warnings.push({
      code: "usage_missing",
      message: `Usage field ${fieldName} was missing; RunCost could not extract billable usage from it.`,
      path: fieldName,
      metadata: { field: fieldName }
    });
  }
  for (const field of metadata.inclusive_usage_fields || []) {
    const fieldName = String(field);
    warnings.push({
      code: "inclusive_usage_ambiguous",
      message: `Usage field ${fieldName} appears inclusive; RunCost priced component fields instead.`,
      path: fieldName,
      metadata: { field: fieldName }
    });
  }
  return warnings;
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
  if (match.tags && typeof match.tags === "object" && !Array.isArray(match.tags)) {
    const actualTags = normalizeAttribution(usageLedger.attribution).tags || {};
    if (Object.entries(match.tags).some(([key, value]) => actualTags[String(key)] !== String(value))) {
      return false;
    }
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

function discountNotAppliedWarnings(policies, appliedDiscounts) {
  const appliedPolicyIds = new Set(appliedDiscounts.map((discount) => discount.policy_id));
  const warnings = [];
  for (const policy of policies) {
    if (policy.metadata?.warn_if_unapplied !== true) {
      continue;
    }
    if (appliedPolicyIds.has(policy.id)) {
      continue;
    }
    warnings.push({
      code: "discount_not_applied",
      message: `Discount policy ${policy.id} did not apply to any priced component.`,
      metadata: {
        policy_id: policy.id
      }
    });
  }
  return warnings;
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
  const context = usageContext(usageLedger);
  const pricedAt = dateValue(context.priced_at || context.pricedAt);
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
    message: `Price source ${(card.source || {}).name || "unknown"} is ${ageDays} days old; threshold is ${threshold} days.`,
    metadata: {
      source: (card.source || {}).name || "unknown",
      age_days: ageDays,
      threshold_days: threshold,
      retrieved_at: (card.source || {}).retrieved_at,
      priced_at: datePart(usageContext(usageLedger).priced_at)
    }
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
    message: `Provider reported cost ${providerTotal} differs from calculated total ${total}.`,
    metadata: {
      provider_reported_cost: providerTotal,
      calculated_total: total
    }
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
    message: `Provider reported cost ${providerTotal} used as authoritative total.`,
    metadata: {
      provider_reported_cost: providerTotal,
      calculated_total: total
    }
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
    message: `Multiple price sources disagree for ${component.name}; using ${matches[0].card.id}.`,
    metadata: {
      component: component.name,
      selected_price_card_id: matches[0].card.id,
      candidate_price_card_ids: matches.map(({ card }) => card.id)
    }
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
  const compiledCatalog = compilePriceCatalog(priceCards);
  priceCards = compiledCatalog.priceCards;
  const components = [];
  const warnings = usageMetadataFieldWarnings(usageLedger);
  const appliedDiscounts = [];
  const sourceByName = new Map();
  const trace = debugTraceEnabled(debugTrace ?? debug_trace) ? newDebugTrace() : null;
  let total = "0";
  let resolvedBilledModel = billedModel(usageLedger);
  let aliasResolution = usageLedger.model.alias_resolution || "none";
  const sourcePriority = priceSourcePriority || price_source_priority || [];
  const warnedUnknownModel = new Set();
  const warnedUnknownProvider = new Set();
  const warnedNoMatchingCard = new Set();
  let warnedAliasInferred = false;
  const warnedStaleCards = new Set();
  const serviceTierFallbackCardIds = new Set();
  const staleThreshold = staleAfterDays ?? stale_after_days;
  const reportedCost = providerReportedCost ?? provider_reported_cost;
  const reportedCostMode = providerReportedCostMode ?? provider_reported_cost_mode ?? "compare";
  const priceLookupCache = new Map();

  for (const component of usageLedger.components) {
    const componentUsageLedger = usageLedgerForComponent(usageLedger, component);
    const componentBilledModel = billedModel(componentUsageLedger);
    const componentWarningKey = [
      componentUsageLedger.provider,
      componentUsageLedger.surface,
      componentBilledModel
    ].join("|");
    const lookupKey = priceLookupCacheKey(componentUsageLedger, sourcePriority);
    let lookup = priceLookupCache.get(lookupKey);
    if (!lookup) {
      const identityCandidates = compiledIdentityCandidates(compiledCatalog, componentUsageLedger);
      const modelCandidates = compiledModelCandidates(compiledCatalog, componentUsageLedger);
      lookup = {
        hasModelCard: hasPriceCardForUsage(componentUsageLedger, identityCandidates),
        modelSurfaceCardExists: hasPriceCardForModelSurface(componentUsageLedger, modelCandidates),
        candidateCards: matchingCards(componentUsageLedger, identityCandidates, sourcePriority),
        identityCandidates
      };
      priceLookupCache.set(lookupKey, lookup);
    }
    const { hasModelCard, modelSurfaceCardExists, candidateCards } = lookup;
    if (trace) {
      trace.decisions.push({
        type: "price_card_candidates",
        component: component.name,
        model: componentBilledModel,
        candidate_price_card_ids: candidateCards.map((card) => card.id),
        source_priority: sourcePriority
      });
    }

    if (!hasModelCard) {
      if (modelSurfaceCardExists) {
        if (!warnedUnknownProvider.has(componentWarningKey)) {
          warnings.push(unknownProviderWarning(componentUsageLedger));
          warnedUnknownProvider.add(componentWarningKey);
        }
      } else if (!warnedUnknownModel.has(componentWarningKey)) {
        warnings.push(unknownModelWarning(componentUsageLedger));
        warnedUnknownModel.add(componentWarningKey);
      }
      if (trace) {
        trace.summary.unpriced_components += 1;
      }
      continue;
    }

    if (candidateCards.length === 0) {
      if (!warnedNoMatchingCard.has(componentWarningKey)) {
        warnings.push(noMatchingCardWarning(componentUsageLedger, lookup.identityCandidates));
        warnedNoMatchingCard.add(componentWarningKey);
      }
      if (trace) {
        trace.summary.unpriced_components += 1;
      }
      continue;
    }

    const candidates = authoritativeSourceCandidates(
      componentUsageLedger,
      candidatePriceComponents(candidateCards, component),
      sourcePriority
    );
    let matches = candidates.filter(({ priceComponent }) => {
      return conditionsMatch(componentUsageLedger, priceComponent);
    });
    if (matches.length === 0 && candidates.length === 0) {
      matches = outputReasoningPricedAsOutputMatches(componentUsageLedger, candidateCards, component);
    }
    if (matches.length === 0) {
      const capabilityWarning = sourceCapabilityWarning(candidateCards, component);
      const longContextWarning = longContextRuleMissingWarning(componentUsageLedger, candidates, component);
      if (capabilityWarning) {
        warnings.push(capabilityWarning);
      } else if (longContextWarning) {
        warnings.push(longContextWarning);
      } else {
        warnings.push(unpricedComponentWarning(componentUsageLedger, component));
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
    const { card, priceComponent, componentMetadata } = match;
    const resolvedComponentMetadata = { ...(componentMetadata || {}) };
    const serviceTierResolution = serviceTierFallbackMetadata(componentUsageLedger, card);
    if (serviceTierResolution) {
      resolvedComponentMetadata.service_tier_resolution = serviceTierResolution;
      serviceTierFallbackCardIds.add(card.id);
    }
    const periodSelection = pricingPeriodSelection(componentUsageLedger, card);
    const periodMetadata = {};
    if (periodSelection.pricing_period === cardPricingPeriod(card)) {
      for (const key of ["pricing_period", "period_selection", "pricing_window", "pricing_timezone"]) {
        if (periodSelection[key] !== undefined) {
          periodMetadata[key] = periodSelection[key];
        }
      }
    }
    if (trace) {
      const decision = {
        type: "price_component_match",
        component: component.name,
        candidate_price_card_ids: matches.map(({ card: matchedCard }) => matchedCard.id),
        selected_price_card_id: card.id,
        selected_source: card.source.name,
        ...periodMetadata
      };
      if (serviceTierResolution) decision.service_tier_resolution = serviceTierResolution;
      trace.decisions.push(decision);
    }
    if (card.model !== componentBilledModel && (card.aliases || []).includes(componentBilledModel)) {
      const previousBilledModel = componentBilledModel;
      if (!componentBillingModel(component)) {
        resolvedBilledModel = card.model;
        if (aliasResolution === "none") {
          aliasResolution = "source_exact";
          if (!warnedAliasInferred) {
            warnings.push(aliasInferredWarning(previousBilledModel, resolvedBilledModel));
            warnedAliasInferred = true;
          }
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
      componentUsageLedger,
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
      const staleWarning = stalePriceWarning(componentUsageLedger, card, staleThreshold);
      if (staleWarning) {
        warnings.push(staleWarning);
        warnedStaleCards.add(card.id);
      }
    }

    const costComponent = {
      name: component.name,
      quantity: component.quantity,
      unit: component.unit,
      unit_price: multiplyDivideDecimal(priceComponent.price.amount, "1", priceComponent.price.per),
      cost: discounted.cost,
      price_card_id: card.id,
      discount_eligible: discountEligible
    };
    const outputMetadata = {
      ...(component.metadata && typeof component.metadata === "object" ? component.metadata : {})
    };
    Object.assign(outputMetadata, periodMetadata);
    Object.assign(outputMetadata, resolvedComponentMetadata);
    if (Object.keys(outputMetadata).length > 0) {
      costComponent.metadata = outputMetadata;
    }
    components.push(costComponent);
    if (trace) {
      trace.summary.priced_components += 1;
    }
  }

  total = applyProviderReportedCostUse(total, components, warnings, reportedCost, reportedCostMode);
  const reportedWarning = providerReportedWarning(total, reportedCost, reportedCostMode);
  if (reportedWarning) {
    warnings.push(reportedWarning);
  }
  warnings.push(...discountNotAppliedWarnings(discountPolicies, appliedDiscounts));
  const orderedComponents = orderedCostComponents(components);
  const orderedSources = orderedPriceSources([...sourceByName.values()]);
  const orderedDiscounts = orderedAppliedDiscounts(appliedDiscounts);
  const orderedWarningList = orderedWarnings(warnings);
  if (trace) {
    for (const warning of orderedWarningList) {
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
    components: orderedComponents,
    total,
    price_sources: orderedSources,
    applied_discounts: orderedDiscounts,
    warnings: orderedWarningList
  };
  if (trace) {
    result.debug_trace = trace;
  }
  if (usageLedger.metadata && typeof usageLedger.metadata === "object" && Object.keys(usageLedger.metadata).length > 0) {
    result.metadata = { ...usageLedger.metadata };
  }
  if (serviceTierFallbackCardIds.size > 0) {
    result.metadata = {
      ...(result.metadata || {}),
      service_tier_resolution: {
        requested: "fast",
        priced_as: "priority",
        fallback: true,
        price_card_ids: [...serviceTierFallbackCardIds].sort()
      }
    };
  }
  const normalizedAttribution = normalizeAttribution(usageLedger.attribution);
  if (Object.keys(normalizedAttribution).length > 0) {
    result.attribution = normalizedAttribution;
  }
  if (mode === "strict" && orderedWarningList.length > 0) {
    throw new Error(`strict mode cost calculation failed: ${orderedWarningList[0].code}`);
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
  stream_final_usage_present,
  attribution
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

  const orderedWarningList = orderedWarnings(warnings);
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
    components: orderedCostComponents([...componentsByKey.values()]),
    total,
    price_sources: orderedPriceSources([...sourceByKey.values()]),
    applied_discounts: orderedAppliedDiscounts(appliedDiscounts),
    warnings: orderedWarningList,
    metadata
  };
  const normalizedAttribution = normalizeAttribution(attribution);
  if (Object.keys(normalizedAttribution).length > 0) {
    result.attribution = normalizedAttribution;
  }
  if (mode === "strict" && orderedWarningList.length > 0) {
    throw new Error(`strict mode cost aggregation failed: ${orderedWarningList[0].code}`);
  }
  return result;
}

function numberString(value) {
  return normalizeDecimalString(value);
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

function positiveComponentWithMetadata(name, quantity, unit, sourcePath, metadata) {
  const component = positiveComponent(name, quantity, unit, sourcePath);
  if (!component) {
    return null;
  }
  const result = {
    ...component,
    metadata: { ...metadata }
  };
  if (metadata.billing_model) {
    result.billing_model = String(metadata.billing_model);
  }
  return result;
}

function componentBillingModel(component) {
  const value = component.billing_model;
  return value ? String(value) : null;
}

function usageLedgerForComponent(usageLedger, component) {
  const billingModel = componentBillingModel(component);
  if (!billingModel) {
    return usageLedger;
  }
  return {
    ...usageLedger,
    model: {
      ...usageLedger.model,
      returned: billingModel,
      billed: billingModel
    }
  };
}

function compactComponents(components) {
  return components.filter(Boolean);
}

const XAI_SERVER_SIDE_TOOL_USAGE_COMPONENTS = new Map([
  ["SERVER_SIDE_TOOL_WEB_SEARCH", ["web_search_units", "search"]],
  ["SERVER_SIDE_TOOL_IMAGE_SEARCH", ["web_search_units", "search"]],
  ["SERVER_SIDE_TOOL_X_SEARCH", ["x_search_units", "search"]],
  ["SERVER_SIDE_TOOL_CODE_EXECUTION", ["code_interpreter_call_units", "call"]],
  ["SERVER_SIDE_TOOL_COLLECTIONS_SEARCH", ["file_search_units", "call"]],
  ["SERVER_SIDE_TOOL_ATTACHMENT_SEARCH", ["attachment_search_units", "call"]],
  ["web_search", ["web_search_units", "search"]],
  ["image_search", ["web_search_units", "search"]],
  ["x_search", ["x_search_units", "search"]],
  ["code_execution", ["code_interpreter_call_units", "call"]],
  ["code_interpreter", ["code_interpreter_call_units", "call"]],
  ["collections_search", ["file_search_units", "call"]],
  ["file_search", ["file_search_units", "call"]],
  ["attachment_search", ["attachment_search_units", "call"]]
]);

function xaiServerSideToolUsage(response, usage) {
  const candidates = [
    [response, "server_side_tool_usage", "$.server_side_tool_usage"],
    [response, "serverSideToolUsage", "$.serverSideToolUsage"],
    [usage, "server_side_tool_usage", "$.usage.server_side_tool_usage"],
    [usage, "serverSideToolUsage", "$.usage.serverSideToolUsage"]
  ];
  for (const [parent, key, sourcePath] of candidates) {
    const value = parent && parent[key];
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return { usage: value, sourcePath };
    }
  }
  return { usage: {}, sourcePath: "$.server_side_tool_usage" };
}

function xaiServerSideToolUsageComponents(response, usage) {
  const serverSideToolUsage = xaiServerSideToolUsage(response, usage);
  const components = [];
  let totalCount = 0;
  for (const [rawName, quantity] of Object.entries(serverSideToolUsage.usage)) {
    const mapping = XAI_SERVER_SIDE_TOOL_USAGE_COMPONENTS.get(String(rawName));
    if (!mapping) continue;
    const [componentName, unit] = mapping;
    totalCount += Number(quantity || 0);
    components.push(positiveComponent(componentName, quantity, unit, `${serverSideToolUsage.sourcePath}.${rawName}`));
  }
  return {
    components,
    totalCount,
    hasUsage: Object.keys(serverSideToolUsage.usage).length > 0
  };
}

function baseUsageLedger({ provider, surface, requestedModel, returnedModel, components, rawUsage, context }) {
  const ledger = {
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
  if (context && Object.keys(context).length > 0) {
    ledger.context = context;
  }
  return ledger;
}

function normalizeOpenAIServiceTier(value) {
  const tier = String(value || "").trim().toLowerCase();
  if (!tier) return undefined;
  if (["auto", "default", "standard"].includes(tier)) return "standard";
  return tier;
}

function usageContextFromOptions(response, provider, options = {}) {
  const context = { ...(options.context || {}) };
  if (provider === "openai") {
    const contextTier = context.service_tier ?? context.serviceTier;
    if (contextTier !== undefined && contextTier !== null) {
      const normalizedContextTier = normalizeOpenAIServiceTier(contextTier);
      if (normalizedContextTier) context.service_tier = normalizedContextTier;
      delete context.serviceTier;
    }
  }
  const pricedAt = options.priced_at ?? options.pricedAt;
  if (pricedAt !== undefined && pricedAt !== null) {
    context.priced_at = String(pricedAt);
  } else if (["deepseek", "openai"].includes(provider) && context.priced_at === undefined && context.pricedAt === undefined) {
    const timestamp = provider === "openai" ? (response.created_at ?? response.created) : response.created;
    const createdPricedAt = unixSecondsPricedAt(timestamp);
    if (createdPricedAt) {
      context.priced_at = createdPricedAt;
    }
  }
  const pricingPeriod = options.pricing_period ?? options.pricingPeriod;
  if (pricingPeriod !== undefined && pricingPeriod !== null) {
    context.pricing_period = String(pricingPeriod);
  }
  let serviceTier = options.service_tier ?? options.serviceTier;
  if ((serviceTier === undefined || serviceTier === null) && provider === "openai") {
    serviceTier = response.service_tier ?? response.serviceTier;
  }
  if (serviceTier !== undefined && serviceTier !== null && context.service_tier === undefined) {
    const normalizedTier = provider === "openai" ? normalizeOpenAIServiceTier(serviceTier) : String(serviceTier);
    if (normalizedTier) context.service_tier = normalizedTier;
  }
  return context;
}

function openAIResponsesPayload(response) {
  if (response.type === "response.completed" && response.response) {
    return response.response;
  }
  return response;
}

function openAIResponsesOrchestrationUsage(usage) {
  const inputDetails = usage.input_tokens_details || {};
  const outputDetails = usage.output_tokens_details || {};
  return {
    input: inputDetails.orchestration_input_tokens ?? 0,
    cachedInput: inputDetails.orchestration_input_cached_tokens ?? 0,
    output: outputDetails.orchestration_output_tokens ?? 0
  };
}

function sumOpenAIResponsesOrchestrationUsage(usages) {
  return usages.reduce(
    (total, usage) => {
      const current = openAIResponsesOrchestrationUsage(usage);
      return {
        input: addDecimal(total.input, current.input),
        cachedInput: addDecimal(total.cachedInput, current.cachedInput),
        output: addDecimal(total.output, current.output)
      };
    },
    { input: "0", cachedInput: "0", output: "0" }
  );
}

function xaiProviderReportedCost(response, usageLedger) {
  const provider = String(usageLedger.provider || "").toLowerCase();
  if (provider !== "xai") {
    return undefined;
  }
  const payload = openAIResponsesPayload(response);
  const usage = payload.usage && typeof payload.usage === "object" ? payload.usage : {};
  const ticks = usage.cost_in_usd_ticks ?? usage.costInUsdTicks;
  if (ticks === undefined || ticks === null) {
    return undefined;
  }
  return multiplyDivideDecimal(ticks, "1", "10000000000");
}

function providerReportedCostFromRawResponse(response, usageLedger) {
  return xaiProviderReportedCost(response, usageLedger);
}

export function extractOpenAIResponsesUsage(response, options = {}) {
  response = openAIResponsesPayload(response);
  const usage = response.usage || {};
  const surface = options.surface || "openai.responses";
  const responseProviderDefaults = {
    "xai.responses": "xai",
    "meta.responses": "meta"
  };
  const provider = options.provider || responseProviderDefaults[surface] || "openai";
  const inputDetails = usage.input_tokens_details || {};
  const outputDetails = usage.output_tokens_details || {};
  const cachedInput = inputDetails.cached_tokens ?? 0;
  const cacheWrite = inputDetails.cache_write_tokens ?? 0;
  const reasoning = outputDetails.reasoning_tokens ?? 0;
  const orchestrationUsage = openAIResponsesOrchestrationUsage(usage);
  const input = usage.input_tokens ?? 0;
  const output = usage.output_tokens ?? 0;
  const inputUncached = addDecimal(
    subtractDecimal(subtractDecimal(input, cachedInput), cacheWrite),
    subtractDecimal(orchestrationUsage.input, orchestrationUsage.cachedInput)
  );
  const inputCacheRead = addDecimal(cachedInput, orchestrationUsage.cachedInput);
  const outputText = addDecimal(subtractDecimal(output, reasoning), orchestrationUsage.output);
  const context = usageContextFromOptions(response, provider, options);

  const toolComponents = [];
  let functionCallCount = 0;
  let explicitServerSideToolCount = 0;
  const xaiTypedToolUsage = String(provider).toLowerCase() === "xai"
    ? xaiServerSideToolUsageComponents(response, usage)
    : { components: [], totalCount: 0, hasUsage: false };
  for (const item of response.output || []) {
    if (item.type === "web_search_call") {
      explicitServerSideToolCount += 1;
      if (!xaiTypedToolUsage.hasUsage) {
        toolComponents.push(positiveComponent("web_search_units", 1, "search", "$.output[*].type"));
      }
    } else if (item.type === "file_search_call" || item.type === "collections_search_call") {
      explicitServerSideToolCount += 1;
      if (!xaiTypedToolUsage.hasUsage) {
        toolComponents.push(positiveComponent("file_search_units", 1, "call", "$.output[*].type"));
      }
    } else if (item.type === "code_interpreter_call" || item.type === "code_execution_call") {
      explicitServerSideToolCount += 1;
      if (!xaiTypedToolUsage.hasUsage) {
        toolComponents.push(positiveComponent("code_interpreter_call_units", 1, "call", "$.output[*].type"));
      }
    } else if (item.type === "attachment_search_call") {
      explicitServerSideToolCount += 1;
      if (!xaiTypedToolUsage.hasUsage) {
        toolComponents.push(positiveComponent("attachment_search_units", 1, "call", "$.output[*].type"));
      }
    } else if (item.type === "computer_call") {
      explicitServerSideToolCount += 1;
      const actionCount = Array.isArray(item.actions) ? item.actions.length : 1;
      toolComponents.push(positiveComponent("computer_use_action_units", actionCount, "call", "$.output[*].actions[*]"));
    } else if (item.type === "x_search_call") {
      explicitServerSideToolCount += 1;
      if (!xaiTypedToolUsage.hasUsage) {
        toolComponents.push(positiveComponent("x_search_units", 1, "search", "$.output[*].type"));
      }
    } else if (item.type === "function_call") {
      functionCallCount += 1;
    }
  }
  toolComponents.push(positiveComponent("tool_call_units", functionCallCount, "call", "$.output[*].type"));
  toolComponents.push(...xaiTypedToolUsage.components);
  if (String(provider).toLowerCase() === "xai") {
    const reportedServerSideToolCount = Number(usage.num_server_side_tools_used || usage.numServerSideToolsUsed || 0);
    if (!xaiTypedToolUsage.hasUsage) {
      const remainingServerSideToolCount = reportedServerSideToolCount - explicitServerSideToolCount;
      toolComponents.push(positiveComponent(
        "tool_call_units",
        remainingServerSideToolCount,
        "call",
        "$.usage.num_server_side_tools_used"
      ));
    }
  }

  return baseUsageLedger({
    provider,
    surface,
    requestedModel: options.model || response.model,
    returnedModel: response.model,
    rawUsage: usage,
    context,
    components: compactComponents([
      positiveComponent(
        "input_uncached_tokens",
        inputUncached,
        "token",
        "$.usage.input_tokens + $.usage.input_tokens_details.orchestration_input_tokens"
      ),
      positiveComponent(
        "input_cache_read_tokens",
        inputCacheRead,
        "token",
        "$.usage.input_tokens_details.cached_tokens + $.usage.input_tokens_details.orchestration_input_cached_tokens"
      ),
      positiveComponent("input_cache_write_tokens", cacheWrite, "token", "$.usage.input_tokens_details.cache_write_tokens"),
      positiveComponent(
        "output_text_tokens",
        outputText,
        "token",
        "$.usage.output_tokens + $.usage.output_tokens_details.orchestration_output_tokens"
      ),
      positiveComponent("output_reasoning_tokens", reasoning, "token", "$.usage.output_tokens_details.reasoning_tokens"),
      ...toolComponents
    ])
  });
}

export function extractOpenAIEmbeddingsUsage(response, options = {}) {
  const usage = response.usage || {};
  const tokens = hasOwn(usage, "prompt_tokens") ? usage.prompt_tokens : usage.total_tokens || 0;
  const sourcePath = hasOwn(usage, "prompt_tokens") ? "$.usage.prompt_tokens" : "$.usage.total_tokens";

  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.embeddings",
    requestedModel: options.model || response.model,
    returnedModel: response.model,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("embedding_tokens", tokens, "token", sourcePath)
    ])
  });
}

function transcriptionDurationSeconds(response) {
  const usage = response.usage && typeof response.usage === "object" ? response.usage : {};
  if (usage.type === "duration" || hasOwn(usage, "seconds")) {
    return { value: usage.seconds || 0, sourcePath: "$.usage.seconds" };
  }
  for (const [field, sourcePath] of [
    ["duration", "$.duration"],
    ["durationInSeconds", "$.durationInSeconds"],
    ["duration_in_seconds", "$.duration_in_seconds"]
  ]) {
    if (response[field] !== undefined && response[field] !== null) {
      return { value: response[field], sourcePath };
    }
  }
  const finish = response.finish && typeof response.finish === "object" ? response.finish : {};
  for (const [field, sourcePath] of [
    ["durationInSeconds", "$.finish.durationInSeconds"],
    ["duration_in_seconds", "$.finish.duration_in_seconds"],
    ["duration", "$.finish.duration"]
  ]) {
    if (finish[field] !== undefined && finish[field] !== null) {
      return { value: finish[field], sourcePath };
    }
  }
  return { value: undefined, sourcePath: undefined };
}

function vercelAISDKModelId(response) {
  const responseMetadata = response.response && typeof response.response === "object" ? response.response : {};
  const modelMetadata = response.model && typeof response.model === "object" ? response.model : {};
  for (const value of [
    response.model,
    responseMetadata.modelId,
    responseMetadata.model_id,
    modelMetadata.modelId,
    modelMetadata.model_id
  ]) {
    if (typeof value === "string" && value) return value;
  }
  return undefined;
}

export function extractOpenAIAudioTranscriptionUsage(response, options = {}) {
  const usage = response.usage && typeof response.usage === "object" ? response.usage : {};
  const components = [];
  if (usage.type === "duration" || hasOwn(usage, "seconds")) {
    components.push(positiveComponent("transcription_seconds", usage.seconds || 0, "second", "$.usage.seconds"));
  } else if (Object.keys(usage).length > 0) {
    const inputDetails = usage.input_token_details || {};
    const audioTokens = inputDetails.audio_tokens || 0;
    const inputTokens = usage.input_tokens || 0;
    const textTokens = hasOwn(inputDetails, "text_tokens") ? inputDetails.text_tokens : inputTokens - audioTokens;
    const outputTokens = usage.output_tokens || 0;
    components.push(
      positiveComponent("input_uncached_tokens", textTokens, "token", "$.usage.input_token_details.text_tokens"),
      positiveComponent("input_audio_tokens", audioTokens, "token", "$.usage.input_token_details.audio_tokens"),
      positiveComponent("output_text_tokens", outputTokens, "token", "$.usage.output_tokens")
    );
  } else {
    const duration = transcriptionDurationSeconds(response);
    if (duration.value !== undefined && duration.sourcePath !== undefined) {
      components.push(positiveComponent("transcription_seconds", duration.value, "second", duration.sourcePath));
    }
  }

  const returnedModel = vercelAISDKModelId(response) || options.model;
  const duration = transcriptionDurationSeconds(response);
  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.audio_transcriptions",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: Object.keys(usage).length > 0 ? usage : {
      duration_seconds: duration.value,
      source_path: duration.sourcePath
    },
    components: compactComponents(components)
  });
}

export function extractOpenAIImagesUsage(response, options = {}) {
  const usage = response.usage && typeof response.usage === "object" ? response.usage : {};
  const components = [];
  if (Object.keys(usage).length > 0) {
    const inputDetails = usage.input_tokens_details || {};
    const inputImageTokens = inputDetails.image_tokens || 0;
    const inputTokens = usage.input_tokens || 0;
    const inputTextTokens = hasOwn(inputDetails, "text_tokens") ? inputDetails.text_tokens : inputTokens - inputImageTokens;
    const outputDetails = usage.output_tokens_details || {};
    const outputImageTokens = hasOwn(outputDetails, "image_tokens") ? outputDetails.image_tokens : usage.output_tokens || 0;
    components.push(
      positiveComponent("input_uncached_tokens", inputTextTokens, "token", "$.usage.input_tokens_details.text_tokens"),
      positiveComponent("input_image_tokens", inputImageTokens, "token", "$.usage.input_tokens_details.image_tokens"),
      positiveComponent("output_image_tokens", outputImageTokens, "token", "$.usage.output_tokens")
    );
  } else {
    const images = Array.isArray(response.data) ? response.data : [];
    components.push(positiveComponent("image_generation_units", images.length, "image", "$.data"));
  }

  const returnedModel = response.model || options.model;
  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.images",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: Object.keys(usage).length > 0 ? usage : { image_count: Array.isArray(response.data) ? response.data.length : 0 },
    components: compactComponents(components)
  });
}

function openAIUsageImagesCount(response) {
  if (response.object === "organization.usage.images.result") {
    return response.images ?? 0;
  }
  let total = "0";
  if (Array.isArray(response.data)) {
    for (const bucket of response.data) {
      const results = bucket && Array.isArray(bucket.results) ? bucket.results : [];
      for (const result of results) {
        total = addDecimal(total, result && result.images !== undefined ? result.images : 0);
      }
    }
  }
  if (parseDecimal(total).value === 0n && response.images !== undefined) {
    total = addDecimal(total, response.images);
  }
  return total;
}

function openAIUsageFirstResultValue(response, key) {
  if (response[key] !== undefined && response[key] !== null) {
    return response[key];
  }
  if (Array.isArray(response.data)) {
    for (const bucket of response.data) {
      const results = bucket && Array.isArray(bucket.results) ? bucket.results : [];
      for (const result of results) {
        if (result && result[key] !== undefined && result[key] !== null) {
          return result[key];
        }
      }
    }
  }
  return undefined;
}

function openAIUsageSumResultValue(response, key) {
  if (response[key] !== undefined && response[key] !== null) {
    return response[key];
  }
  let total = "0";
  if (Array.isArray(response.data)) {
    for (const bucket of response.data) {
      const results = bucket && Array.isArray(bucket.results) ? bucket.results : [];
      for (const result of results) {
        total = addDecimal(total, result && result[key] !== undefined ? result[key] : 0);
      }
    }
  }
  return total;
}

export function extractOpenAIUsageCompletionsUsage(response, options = {}) {
  const inputTokens = openAIUsageSumResultValue(response, "input_tokens");
  const cachedTokens = openAIUsageSumResultValue(response, "input_cached_tokens");
  const uncachedDifference = subtractDecimal(inputTokens, cachedTokens);
  const uncachedTokens = parseDecimal(uncachedDifference).value < 0n ? "0" : uncachedDifference;
  const outputTokens = openAIUsageSumResultValue(response, "output_tokens");
  const inputAudioTokens = openAIUsageSumResultValue(response, "input_audio_tokens");
  const outputAudioTokens = openAIUsageSumResultValue(response, "output_audio_tokens");
  const numModelRequests = openAIUsageSumResultValue(response, "num_model_requests");
  const returnedModel = response.model || options.model || openAIUsageFirstResultValue(response, "model") || "completions";
  const rawUsage = {
    input_tokens: inputTokens,
    input_cached_tokens: cachedTokens,
    output_tokens: outputTokens,
    input_audio_tokens: inputAudioTokens,
    output_audio_tokens: outputAudioTokens,
    num_model_requests: numModelRequests,
    batch: openAIUsageFirstResultValue(response, "batch"),
    service_tier: openAIUsageFirstResultValue(response, "service_tier")
  };
  Object.keys(rawUsage).forEach((key) => {
    if (rawUsage[key] === undefined || rawUsage[key] === null) {
      delete rawUsage[key];
    }
  });
  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.usage.completions",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", uncachedTokens, "token", "$..input_tokens"),
      positiveComponent("input_cache_read_tokens", cachedTokens, "token", "$..input_cached_tokens"),
      positiveComponent("input_audio_tokens", inputAudioTokens, "token", "$..input_audio_tokens"),
      positiveComponent("output_text_tokens", outputTokens, "token", "$..output_tokens"),
      positiveComponent("output_audio_tokens", outputAudioTokens, "token", "$..output_audio_tokens")
    ])
  });
}

export function extractOpenAIUsageImagesUsage(response, options = {}) {
  const images = openAIUsageImagesCount(response);
  const returnedModel = response.model || options.model || openAIUsageFirstResultValue(response, "model") || "image-generation";
  const rawUsage = {
    images,
    num_model_requests: openAIUsageFirstResultValue(response, "num_model_requests"),
    source: openAIUsageFirstResultValue(response, "source"),
    size: openAIUsageFirstResultValue(response, "size")
  };
  Object.keys(rawUsage).forEach((key) => {
    if (rawUsage[key] === undefined || rawUsage[key] === null) {
      delete rawUsage[key];
    }
  });
  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.usage.images",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage,
    components: compactComponents([
      positiveComponent("image_generation_units", images, "image", "$..images")
    ])
  });
}

function openAIUsageAudioSpeechCharacters(response) {
  if (response.object === "organization.usage.audio_speeches.result") {
    return response.characters ?? 0;
  }
  let total = "0";
  if (Array.isArray(response.data)) {
    for (const bucket of response.data) {
      const results = bucket && Array.isArray(bucket.results) ? bucket.results : [];
      for (const result of results) {
        total = addDecimal(total, result && result.characters !== undefined ? result.characters : 0);
      }
    }
  }
  if (parseDecimal(total).value === 0n && response.characters !== undefined) {
    total = addDecimal(total, response.characters);
  }
  return total;
}

export function extractOpenAIUsageAudioSpeechesUsage(response, options = {}) {
  const characters = openAIUsageAudioSpeechCharacters(response);
  const returnedModel = response.model || options.model || openAIUsageFirstResultValue(response, "model") || "audio-speech";
  const rawUsage = {
    characters,
    num_model_requests: openAIUsageFirstResultValue(response, "num_model_requests")
  };
  Object.keys(rawUsage).forEach((key) => {
    if (rawUsage[key] === undefined || rawUsage[key] === null) {
      delete rawUsage[key];
    }
  });
  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.usage.audio_speeches",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage,
    components: compactComponents([
      positiveComponent("audio_generation_characters", characters, "character", "$..characters")
    ])
  });
}

function openAIUsageAudioTranscriptionSeconds(response) {
  if (response.object === "organization.usage.audio_transcriptions.result") {
    return response.seconds ?? 0;
  }
  let total = "0";
  if (Array.isArray(response.data)) {
    for (const bucket of response.data) {
      const results = bucket && Array.isArray(bucket.results) ? bucket.results : [];
      for (const result of results) {
        total = addDecimal(total, result && result.seconds !== undefined ? result.seconds : 0);
      }
    }
  }
  if (parseDecimal(total).value === 0n && response.seconds !== undefined) {
    total = addDecimal(total, response.seconds);
  }
  return total;
}

export function extractOpenAIUsageAudioTranscriptionsUsage(response, options = {}) {
  const seconds = openAIUsageAudioTranscriptionSeconds(response);
  const returnedModel = response.model || options.model || openAIUsageFirstResultValue(response, "model") || "audio-transcription";
  const rawUsage = {
    seconds,
    num_model_requests: openAIUsageFirstResultValue(response, "num_model_requests")
  };
  Object.keys(rawUsage).forEach((key) => {
    if (rawUsage[key] === undefined || rawUsage[key] === null) {
      delete rawUsage[key];
    }
  });
  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.usage.audio_transcriptions",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage,
    components: compactComponents([
      positiveComponent("transcription_seconds", seconds, "second", "$..seconds")
    ])
  });
}

function openAIUsageEmbeddingTokens(response) {
  if (response.object === "organization.usage.embeddings.result") {
    return response.input_tokens ?? 0;
  }
  let total = "0";
  if (Array.isArray(response.data)) {
    for (const bucket of response.data) {
      const results = bucket && Array.isArray(bucket.results) ? bucket.results : [];
      for (const result of results) {
        total = addDecimal(total, result && result.input_tokens !== undefined ? result.input_tokens : 0);
      }
    }
  }
  if (parseDecimal(total).value === 0n && response.input_tokens !== undefined) {
    total = addDecimal(total, response.input_tokens);
  }
  return total;
}

export function extractOpenAIUsageEmbeddingsUsage(response, options = {}) {
  const inputTokens = openAIUsageEmbeddingTokens(response);
  const returnedModel = response.model || options.model || openAIUsageFirstResultValue(response, "model") || "embedding";
  const rawUsage = {
    input_tokens: inputTokens,
    num_model_requests: openAIUsageFirstResultValue(response, "num_model_requests")
  };
  Object.keys(rawUsage).forEach((key) => {
    if (rawUsage[key] === undefined || rawUsage[key] === null) {
      delete rawUsage[key];
    }
  });
  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.usage.embeddings",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage,
    components: compactComponents([
      positiveComponent("embedding_tokens", inputTokens, "token", "$..input_tokens")
    ])
  });
}

export function extractOpenAIVectorStoreStorageUsage(response, options = {}) {
  const usageBytes = response.usage_bytes ?? 0;
  const storageDays = options.storage_days ?? options.storageDays ?? 0;
  const components = [];
  if (storageDays) {
    const quantity = multiplyDivideDecimal(usageBytes, storageDays, "1000000000");
    components.push(positiveComponent("storage_gb_days", quantity, "gb_day", "$.usage_bytes"));
  }

  const returnedModel = response.model || options.model || "vector-store-storage";
  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.vector_stores",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: {
      usage_bytes: usageBytes,
      storage_days: storageDays
    },
    components: compactComponents(components)
  });
}

function openAIUsageCodeInterpreterSessionCount(response) {
  if (response.object === "organization.usage.code_interpreter_sessions.result") {
    return response.num_sessions ?? 0;
  }
  let total = "0";
  if (Array.isArray(response.data)) {
    for (const bucket of response.data) {
      const results = bucket && Array.isArray(bucket.results) ? bucket.results : [];
      for (const result of results) {
        total = addDecimal(total, result && result.num_sessions !== undefined ? result.num_sessions : 0);
      }
    }
  }
  if (parseDecimal(total).value === 0n && response.num_sessions !== undefined) {
    total = addDecimal(total, response.num_sessions);
  }
  return total;
}

export function extractOpenAIUsageCodeInterpreterSessionsUsage(response, options = {}) {
  const numSessions = openAIUsageCodeInterpreterSessionCount(response);
  const returnedModel = response.model || options.model || "code-interpreter-session";
  return baseUsageLedger({
    provider: options.provider || "openai",
    surface: options.surface || "openai.usage.code_interpreter_sessions",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: {
      num_sessions: numSessions
    },
    components: compactComponents([
      positiveComponent("code_interpreter_session_units", numSessions, "session", "$..num_sessions")
    ])
  });
}

const OPENAI_COMPATIBLE_CHAT_PROVIDERS = {
  "openai.chat_completions": "openai",
  "openrouter.chat_completions": "openrouter",
  "groq.chat_completions": "groq",
  "xai.chat_completions": "xai",
  "meta.chat_completions": "meta",
  "mistral.chat_completions": "mistral",
  "deepseek.chat_completions": "deepseek",
  "azure.openai.chat_completions": "azure",
  "huggingface.chat_completions": "huggingface",
  "nvidia.chat_completions": "nvidia",
  "tinker.chat_completions": "tinker",
  "kimi.chat_completions": "kimi",
  "ai21.chat_completions": "ai21",
  "arcee.chat_completions": "arcee",
  "cohere.chat_completions_compatible": "cohere",
  "dashscope.chat_completions": "dashscope",
  "inception.chat_completions": "inception",
  "poolside.chat_completions": "poolside",
  "xiaomi.chat_completions": "xiaomi",
  "zai.chat_completions": "zai",
  "zhipu.chat_completions": "zhipu"
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

function openAICompatibleCacheWrite(usage) {
  if (hasOwn(usage.prompt_tokens_details || {}, "cache_write_tokens")) {
    return {
      value: usage.prompt_tokens_details.cache_write_tokens || 0,
      sourcePath: "$.usage.prompt_tokens_details.cache_write_tokens"
    };
  }
  return {
    value: 0,
    sourcePath: "$.usage.prompt_tokens_details.cache_write_tokens"
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

function openAICompatibleChatPayload(response) {
  const chunks = response.chunks || response.stream;
  if (!Array.isArray(chunks)) {
    return response;
  }
  const fallbackServiceTier = response.service_tier ?? response.serviceTier ??
    chunks.find((chunk) => chunk && typeof chunk === "object" && (chunk.service_tier ?? chunk.serviceTier) != null)?.service_tier ??
    chunks.find((chunk) => chunk && typeof chunk === "object" && chunk.serviceTier != null)?.serviceTier;
  for (let index = chunks.length - 1; index >= 0; index -= 1) {
    const chunk = chunks[index];
    if (chunk && typeof chunk === "object" && chunk.usage && typeof chunk.usage === "object") {
      return {
        ...chunk,
        model: chunk.model ?? response.model,
        service_tier: chunk.service_tier ?? chunk.serviceTier ?? fallbackServiceTier
      };
    }
  }
  return response;
}

export function extractOpenAICompatibleChatCompletionsUsage(response, options = {}) {
  response = openAICompatibleChatPayload(response);
  const usage = response.usage || {};
  const cachedInput = openAICompatibleCachedInput(usage);
  const cacheWrite = openAICompatibleCacheWrite(usage);
  const reasoning = openAICompatibleReasoningOutput(usage);
  const prompt = usage.prompt_tokens ?? ((usage.prompt_cache_hit_tokens || 0) + (usage.prompt_cache_miss_tokens || 0));
  const completion = usage.completion_tokens || 0;
  const surface = options.surface || "openai.chat_completions";
  const provider = options.provider || OPENAI_COMPATIBLE_CHAT_PROVIDERS[surface] || "openai";
  const context = usageContextFromOptions(response, provider, options);

  return baseUsageLedger({
    provider,
    surface,
    requestedModel: options.model || response.model,
    returnedModel: response.model,
    rawUsage: usage,
    context,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", prompt - cachedInput.value - cacheWrite.value, "token", "$.usage.prompt_tokens"),
      positiveComponent("input_cache_read_tokens", cachedInput.value, "token", cachedInput.sourcePath),
      positiveComponent("input_cache_write_tokens", cacheWrite.value, "token", cacheWrite.sourcePath),
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

export function extractMetaChatCompletionsUsage(response, options = {}) {
  return extractOpenAICompatibleChatCompletionsUsage(response, {
    provider: "meta",
    surface: "meta.chat_completions",
    ...options
  });
}

export function extractMetaResponsesUsage(response, options = {}) {
  return extractOpenAIResponsesUsage(response, {
    provider: "meta",
    surface: "meta.responses",
    ...options
  });
}

function anthropicMessagesPayload(response) {
  if (!Array.isArray(response.events)) {
    return response;
  }
  const message = {};
  const usage = {};
  const content = [];
  for (const event of response.events) {
    if (!event || typeof event !== "object") {
      continue;
    }
    if (event.type === "message_start" && event.message) {
      Object.assign(message, event.message);
      Object.assign(usage, event.message.usage || {});
      if (Array.isArray(event.message.content)) {
        content.push(...event.message.content);
      }
    } else if (event.type === "content_block_start" && event.content_block && Number.isInteger(event.index) && event.index >= 0) {
      content[event.index] = { ...event.content_block };
    } else if (event.type === "message_delta") {
      Object.assign(usage, event.usage || {});
      if (event.delta) {
        Object.assign(message, event.delta);
      }
    }
  }
  if (Object.keys(message).length === 0) {
    return response;
  }
  message.usage = usage;
  if (content.length > 0) {
    message.content = content.filter((block) => block !== undefined && block !== null);
  }
  const servingModel = anthropicServingModel(message, usage);
  if (servingModel) {
    message.model = servingModel;
  }
  return message;
}

function anthropicFallbackPairs(response) {
  if (!Array.isArray(response.content)) {
    return [];
  }
  const pairs = [];
  for (const block of response.content) {
    if (!block || typeof block !== "object" || block.type !== "fallback") {
      continue;
    }
    const fromModel = block.from && block.from.model;
    const toModel = block.to && block.to.model;
    if (fromModel && toModel) {
      pairs.push([String(fromModel), String(toModel)]);
    }
  }
  return pairs;
}

function anthropicRefused(response) {
  return response.stop_reason === "refusal";
}

function anthropicIterations(usage) {
  return Array.isArray(usage.iterations)
    ? usage.iterations.filter((iteration) => iteration && typeof iteration === "object")
    : [];
}

function anthropicServingModel(response, usage) {
  const fallbackIterations = anthropicIterations(usage).filter((iteration) => (
    iteration.type === "fallback_message" && iteration.model
  ));
  if (fallbackIterations.length > 0) {
    return String(fallbackIterations[fallbackIterations.length - 1].model);
  }
  return response.model ? String(response.model) : undefined;
}

function anthropicRequestedModel(response, usage, requestedModel) {
  if (requestedModel) return String(requestedModel);
  const pairs = anthropicFallbackPairs(response);
  if (pairs.length > 0) return pairs[0][0];
  const iterations = anthropicIterations(usage);
  if (iterations.length > 1 && iterations[0].model) return String(iterations[0].model);
  return String(response.model || "unknown");
}

function anthropicIterationMetadata(iteration, index, billingModel) {
  const metadata = {
    billing_model: billingModel,
    usage_iteration_index: index
  };
  if (iteration.type) {
    metadata.usage_iteration_type = iteration.type;
  }
  return metadata;
}

function anthropicAttemptRefusedBeforeOutput(response, iteration, index, iterationCount, hasFallbackIteration) {
  if (parseDecimal(iteration.output_tokens || 0).value > 0n) return false;
  if (hasFallbackIteration && index < iterationCount - 1) return true;
  return index === iterationCount - 1 && anthropicRefused(response);
}

function anthropicMessagesIterationComponents(response, usage, requestedModel) {
  const iterations = anthropicIterations(usage);
  if (iterations.length === 0) {
    return [];
  }
  const components = [];
  const hasFallbackIteration = iterations.some((iteration) => (
    iteration.type === "fallback_message"
  ));
  iterations.forEach((iteration, index) => {
    const iterationModel = String(iteration.model || response.model || requestedModel || "");
    const sourceRoot = `$.usage.iterations[${index}]`;
    const metadata = anthropicIterationMetadata(iteration, index, iterationModel);
    const refusedBeforeOutput = anthropicAttemptRefusedBeforeOutput(
      response,
      iteration,
      index,
      iterations.length,
      hasFallbackIteration
    );
    if (!refusedBeforeOutput) {
      const cacheWrite = iteration.cache_creation_input_tokens || 0;
      const cacheWrite1h = iteration.cache_creation_input_tokens_1h || 0;
      components.push(
        positiveComponentWithMetadata("input_uncached_tokens", iteration.input_tokens || 0, "token", `${sourceRoot}.input_tokens`, metadata),
        positiveComponentWithMetadata("input_cache_write_tokens", subtractDecimal(cacheWrite, cacheWrite1h), "token", `${sourceRoot}.cache_creation_input_tokens`, metadata),
        positiveComponentWithMetadata("input_cache_write_1h_tokens", cacheWrite1h, "token", `${sourceRoot}.cache_creation_input_tokens_1h`, metadata),
        positiveComponentWithMetadata("input_cache_read_tokens", iteration.cache_read_input_tokens || 0, "token", `${sourceRoot}.cache_read_input_tokens`, metadata)
      );
      components.push(positiveComponentWithMetadata(
        "output_text_tokens",
        iteration.output_tokens || 0,
        "token",
        `${sourceRoot}.output_tokens`,
        metadata
      ));
    }
  });
  return compactComponents(components);
}

function anthropicClientFallbackCreditEnabled(response, options) {
  for (const key of ["anthropic_fallback_credit", "anthropicFallbackCredit", "fallback_credit", "fallbackCredit"]) {
    if (options[key] === true) {
      return true;
    }
  }
  const request = response.request && typeof response.request === "object" ? response.request : {};
  const metadata = response.metadata && typeof response.metadata === "object" ? response.metadata : {};
  return Boolean(
    request.fallback_credit_token ||
    metadata.fallback_credit_token ||
    response.fallback_credit_token
  );
}

function anthropicResponseMetadata(response, usage, requestedModel, components, fallbackCreditSignaled) {
  const metadata = {};
  const iterations = anthropicIterations(usage);
  const fallbackIterations = iterations.filter((iteration) => iteration.type === "fallback_message");
  const fallbackPairs = anthropicFallbackPairs(response);
  if (fallbackIterations.length > 0 || fallbackPairs.length > 0) {
    const servingModel = anthropicServingModel(response, usage);
    const pricingModels = [];
    for (const component of components) {
      const billingModel = componentBillingModel(component);
      if (billingModel && !pricingModels.includes(billingModel)) pricingModels.push(billingModel);
    }
    if (pricingModels.length === 0 && components.length > 0 && servingModel) pricingModels.push(servingModel);
    const fallback = {
      attempted: true,
      utilized: !anthropicRefused(response),
      requested_model: requestedModel,
      attempted_models: iterations.filter((iteration) => iteration.model).map((iteration) => String(iteration.model)),
      pricing_models: pricingModels,
      source: fallbackIterations.length > 0 ? "usage.iterations" : "content.fallback"
    };
    if (servingModel) fallback.serving_model = servingModel;
    if (fallbackPairs.length > 0) {
      fallback.hops = fallbackPairs.map(([fromModel, toModel]) => ({ from_model: fromModel, to_model: toModel }));
    }
    metadata.anthropic_fallback = fallback;
  }
  if (anthropicRefused(response)) {
    const details = response.stop_details && typeof response.stop_details === "object" ? response.stop_details : {};
    const refusal = {
      detected: true,
      pre_output: parseDecimal(usage.output_tokens || 0).value <= 0n,
      requires_retry: true,
      fallback_credit_available: Boolean(details.fallback_credit_token)
    };
    for (const key of ["category", "recommended_model"]) {
      if (details[key] !== undefined && details[key] !== null) refusal[key] = details[key];
    }
    metadata.anthropic_refusal = refusal;
  }
  if (fallbackCreditSignaled) {
    metadata.anthropic_fallback_credit = { signaled: true, pricing_source: "reported_usage" };
  }
  return metadata;
}

export function extractAnthropicMessagesUsage(response, options = {}) {
  response = anthropicMessagesPayload(response);
  const usagePresent = response.usage && typeof response.usage === "object";
  const usage = usagePresent ? response.usage : {};
  const requestedModel = anthropicRequestedModel(response, usage, options.model);
  const servingModel = anthropicServingModel(response, usage);
  const input = usage.input_tokens || 0;
  const cacheWrite = usage.cache_creation_input_tokens || 0;
  const cacheWrite1h = usage.cache_creation_input_tokens_1h || 0;
  const cacheRead = usage.cache_read_input_tokens || 0;
  const output = usage.output_tokens || 0;
  const metadata = {};
  const refusalZeroBillable = anthropicRefused(response) && parseDecimal(output).value <= 0n;
  const fallbackCreditSignaled = anthropicClientFallbackCreditEnabled(response, options);
  let components = anthropicMessagesIterationComponents(response, usage, requestedModel);
  if (components.length === 0) {
    if (refusalZeroBillable) {
      components = [];
      metadata.zero_billable_reason = "anthropic_classifier_block";
    } else {
      components = compactComponents([
        positiveComponent("input_uncached_tokens", input, "token", "$.usage.input_tokens"),
        positiveComponent("input_cache_write_tokens", cacheWrite - cacheWrite1h, "token", "$.usage.cache_creation_input_tokens"),
        positiveComponent("input_cache_write_1h_tokens", cacheWrite1h, "token", "$.usage.cache_creation_input_tokens_1h"),
        positiveComponent("input_cache_read_tokens", cacheRead, "token", "$.usage.cache_read_input_tokens"),
        positiveComponent("output_text_tokens", output, "token", "$.usage.output_tokens")
      ]);
      if (!usagePresent) {
        metadata.missing_usage_fields = ["$.usage"];
      }
    }
  }
  Object.assign(metadata, anthropicResponseMetadata(
    response,
    usage,
    requestedModel,
    components,
    fallbackCreditSignaled
  ));

  const ledger = baseUsageLedger({
    provider: options.provider || "anthropic",
    surface: options.surface || "anthropic.messages",
    requestedModel,
    returnedModel: servingModel,
    rawUsage: usage,
    components
  });
  if (components.length === 0 && refusalZeroBillable) {
    metadata.zero_billable_reason = metadata.zero_billable_reason || "anthropic_classifier_block";
  }
  if (Object.keys(metadata).length > 0) {
    ledger.metadata = metadata;
  }
  return ledger;
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

function geminiGenerateContentPayload(response) {
  const chunks = response.chunks || response.stream;
  if (!Array.isArray(chunks) || chunks.length === 0) {
    return response;
  }
  for (let index = chunks.length - 1; index >= 0; index -= 1) {
    const chunk = chunks[index];
    if (chunk && typeof chunk === "object" && chunk.usageMetadata) {
      return chunk;
    }
  }
  for (let index = chunks.length - 1; index >= 0; index -= 1) {
    const chunk = chunks[index];
    if (chunk && typeof chunk === "object") {
      return chunk;
    }
  }
  return response;
}

function normalizeGeminiServiceTier(value) {
  if (value === undefined || value === null) return null;
  let tier = String(value).trim();
  if (!tier) return null;
  if (tier.includes(".")) {
    tier = tier.split(".").pop();
  }
  tier = tier.toLowerCase();
  tier = tier.replace(/^service_tier_/, "");
  return tier === "unspecified" ? "standard" : tier;
}

function responseHeaderValue(response, headerName) {
  const expected = headerName.toLowerCase();
  for (const field of ["headers", "response_headers", "responseHeaders"]) {
    const headers = response && typeof response === "object" ? response[field] : null;
    if (!headers || typeof headers !== "object") continue;
    for (const [key, value] of Object.entries(headers)) {
      if (String(key).toLowerCase() === expected) return value;
    }
  }
  return undefined;
}

function geminiHeaderServiceTier(...responses) {
  for (const response of responses) {
    const serviceTier = normalizeGeminiServiceTier(responseHeaderValue(response, "x-gemini-service-tier"));
    if (serviceTier) return serviceTier;
  }
  return null;
}

function geminiUsageContext(usage, response, originalResponse) {
  const serviceTier = geminiHeaderServiceTier(originalResponse, response) ||
    normalizeGeminiServiceTier(usage.serviceTier ?? usage.service_tier);
  return serviceTier ? { service_tier: serviceTier } : null;
}

export function extractGeminiGenerateContentUsage(response, options = {}) {
  const originalResponse = response;
  response = geminiGenerateContentPayload(response);
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

  const ledger = baseUsageLedger({
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
  const context = geminiUsageContext(usage, response, originalResponse);
  if (context) ledger.context = context;
  return ledger;
}

export function extractGeminiLiveUsage(response, options = {}) {
  response = geminiGenerateContentPayload(response);
  const requestedModel = options.model || response.modelVersion;
  const returnedModel = response.modelVersion || options.model;
  const isLiveTranslate = [requestedModel, returnedModel].some(modelNameLooksGeminiLiveTranslate);
  const inputFallbackComponent = isLiveTranslate ? "input_audio_tokens" : "input_uncached_tokens";
  const outputFallbackComponent = isLiveTranslate ? "output_audio_tokens" : "output_text_tokens";
  const usage = response.usageMetadata || {};
  const cachedInput = usage.cachedContentTokenCount || 0;
  const prompt = usage.promptTokenCount || 0;
  const responseTokens = usage.responseTokenCount || 0;
  const thoughts = usage.thoughtsTokenCount || 0;

  const promptCounts = geminiModalityCounts(usage.promptTokensDetails);
  const cacheCounts = geminiModalityCounts(usage.cacheTokensDetails);
  const toolCounts = geminiModalityCounts(usage.toolUsePromptTokensDetails);
  const responseCounts = geminiModalityCounts(usage.responseTokensDetails);

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
        inputFallbackComponent,
        addDecimal(subtractDecimal(prompt, cachedInput), toolPrompt),
        "token",
        "$.usageMetadata.promptTokenCount"
      )
    ];
  }

  let outputComponents;
  if (Object.keys(responseCounts).length > 0) {
    outputComponents = geminiOrderedComponents(
      geminiComponentQuantities(
        responseCounts,
        GEMINI_OUTPUT_MODALITY_COMPONENTS,
        "output_text_tokens"
      ),
      GEMINI_OUTPUT_COMPONENT_ORDER,
      "$.usageMetadata.responseTokensDetails"
    );
  } else {
    outputComponents = [
      positiveComponent(outputFallbackComponent, responseTokens, "token", "$.usageMetadata.responseTokenCount")
    ];
  }

  const ledger = baseUsageLedger({
    provider: options.provider || "google",
    surface: options.surface || "google.gemini.live",
    requestedModel,
    returnedModel,
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
  const context = geminiUsageContext(usage);
  if (context) ledger.context = context;
  return ledger;
}

function googleInteractionsUsageFromParent(parent, sourceRoot) {
  const metadata = parent.metadata && typeof parent.metadata === "object" ? parent.metadata : {};
  for (const key of ["total_usage", "totalUsage", "usage"]) {
    if (metadata[key] && typeof metadata[key] === "object" && !Array.isArray(metadata[key])) {
      return {
        usage: metadata[key],
        sourceRoot: `${sourceRoot}.metadata.${key}`
      };
    }
  }
  for (const key of ["total_usage", "totalUsage", "usage"]) {
    if (parent[key] && typeof parent[key] === "object" && !Array.isArray(parent[key])) {
      return {
        usage: parent[key],
        sourceRoot: `${sourceRoot}.${key}`
      };
    }
  }
  return null;
}

function googleInteractionsUsagePayload(response) {
  let result = googleInteractionsUsageFromParent(response, "$");
  if (result) return result;
  if (response.interaction && typeof response.interaction === "object") {
    result = googleInteractionsUsageFromParent(response.interaction, "$.interaction");
    if (result) return result;
  }
  for (const collectionName of ["chunks", "stream", "events"]) {
    const collection = response[collectionName];
    if (!Array.isArray(collection)) continue;
    for (let index = collection.length - 1; index >= 0; index -= 1) {
      const item = collection[index];
      if (!item || typeof item !== "object") continue;
      result = googleInteractionsUsageFromParent(item, `$.${collectionName}[${index}]`);
      if (result) return result;
    }
  }
  return {
    usage: {},
    sourceRoot: "$.metadata.total_usage"
  };
}

function googleInteractionsResponseValue(response, keys) {
  const directParents = [
    response,
    response.interaction && typeof response.interaction === "object" ? response.interaction : {}
  ];
  for (const parent of directParents) {
    for (const key of keys) {
      if (parent[key]) return parent[key];
    }
  }
  for (const collectionName of ["chunks", "stream", "events"]) {
    const collection = response[collectionName];
    if (!Array.isArray(collection)) continue;
    for (let index = collection.length - 1; index >= 0; index -= 1) {
      const item = collection[index];
      if (!item || typeof item !== "object") continue;
      const parents = [
        item,
        item.interaction && typeof item.interaction === "object" ? item.interaction : {}
      ];
      for (const parent of parents) {
        for (const key of keys) {
          if (parent[key]) return parent[key];
        }
      }
    }
  }
  return undefined;
}

function googleInteractionsServiceTier(response, usage) {
  const headerServiceTier = geminiHeaderServiceTier(response);
  if (headerServiceTier) return headerServiceTier;
  const parents = [
    usage,
    response.metadata && typeof response.metadata === "object" ? response.metadata : {},
    response.interaction && typeof response.interaction === "object" ? response.interaction : {},
    response
  ];
  for (const parent of parents) {
    for (const key of ["service_tier", "serviceTier"]) {
      const serviceTier = normalizeGeminiServiceTier(parent[key]);
      if (serviceTier) return serviceTier;
    }
  }
  return normalizeGeminiServiceTier(googleInteractionsResponseValue(response, ["service_tier", "serviceTier"]));
}

function googleInteractionsModalityCounts(value) {
  const counts = {};
  if (!Array.isArray(value)) {
    return counts;
  }
  for (const detail of value) {
    if (!detail || typeof detail !== "object") continue;
    const modality = String(detail.modality || "text").trim().toUpperCase() || "TEXT";
    addGeminiCount(counts, modality, detail.tokens ?? detail.tokenCount ?? 0);
  }
  return counts;
}

const GOOGLE_INTERACTIONS_GROUNDING_COMPONENTS = new Map([
  ["google_search", ["web_search_units", "search"]],
  ["google_maps", ["tool_call_units", "call"]],
  ["retrieval", ["tool_call_units", "call"]]
]);

function googleInteractionsGroundingComponents(usage, sourceRoot) {
  const groundingCounts = usage.grounding_tool_count;
  if (!Array.isArray(groundingCounts)) {
    return [];
  }
  const totals = new Map();
  for (const detail of groundingCounts) {
    if (!detail || typeof detail !== "object") continue;
    const mapping = GOOGLE_INTERACTIONS_GROUNDING_COMPONENTS.get(String(detail.type || ""));
    if (!mapping) continue;
    const [componentName, unit] = mapping;
    const key = `${componentName}\t${unit}`;
    totals.set(key, addDecimal(totals.get(key) || "0", detail.count || 0));
  }
  return [...totals.entries()].map(([key, quantity]) => {
    const [componentName, unit] = key.split("\t");
    return positiveComponent(componentName, quantity, unit, `${sourceRoot}.grounding_tool_count[*].count`);
  });
}

export function extractGoogleInteractionsUsage(response, options = {}) {
  const { usage, sourceRoot } = googleInteractionsUsagePayload(response);
  const cachedInput = usage.total_cached_tokens || 0;
  const inputTokens = usage.total_input_tokens || 0;
  const outputTokens = usage.total_output_tokens || 0;
  const thoughts = usage.total_thought_tokens || 0;
  const toolUseTokens = usage.total_tool_use_tokens || 0;

  const inputCounts = googleInteractionsModalityCounts(usage.input_tokens_by_modality);
  const cacheCounts = googleInteractionsModalityCounts(usage.cached_tokens_by_modality);
  const outputCounts = googleInteractionsModalityCounts(usage.output_tokens_by_modality);
  const toolCounts = googleInteractionsModalityCounts(usage.tool_use_tokens_by_modality);

  const toolRemainder = subtractDecimal(toolUseTokens, geminiSumCounts(toolCounts));
  if (isPositiveDecimal(toolRemainder)) {
    addGeminiCount(toolCounts, "TEXT", toolRemainder);
  }

  const detailSafeForInput = Object.keys(inputCounts).length > 0 &&
    (!isPositiveDecimal(cachedInput) || Object.keys(cacheCounts).length > 0);
  let inputComponents;
  let cacheRead = cachedInput;
  let cacheReadSource = `${sourceRoot}.total_cached_tokens`;
  if (detailSafeForInput) {
    inputComponents = geminiOrderedComponents(
      geminiComponentQuantities(
        geminiNetInputCounts(inputCounts, cacheCounts, toolCounts),
        GEMINI_INPUT_MODALITY_COMPONENTS,
        "input_uncached_tokens"
      ),
      GEMINI_INPUT_COMPONENT_ORDER,
      `${sourceRoot}.input_tokens_by_modality`
    );
    cacheRead = isPositiveDecimal(cachedInput) ? cachedInput : geminiSumCounts(cacheCounts);
    if (!hasOwn(usage, "total_cached_tokens")) {
      cacheReadSource = `${sourceRoot}.cached_tokens_by_modality`;
    }
  } else {
    inputComponents = [
      positiveComponent(
        "input_uncached_tokens",
        addDecimal(subtractDecimal(inputTokens, cachedInput), toolUseTokens),
        "token",
        `${sourceRoot}.total_input_tokens`
      )
    ];
  }

  let outputComponents;
  if (Object.keys(outputCounts).length > 0) {
    outputComponents = geminiOrderedComponents(
      geminiComponentQuantities(
        outputCounts,
        GEMINI_OUTPUT_MODALITY_COMPONENTS,
        "output_text_tokens"
      ),
      GEMINI_OUTPUT_COMPONENT_ORDER,
      `${sourceRoot}.output_tokens_by_modality`
    );
  } else {
    outputComponents = [
      positiveComponent("output_text_tokens", outputTokens, "token", `${sourceRoot}.total_output_tokens`)
    ];
  }

  const returnedModel = googleInteractionsResponseValue(response, ["model", "agent"]) || options.model;
  const ledger = baseUsageLedger({
    provider: options.provider || "google",
    surface: options.surface || "google.gemini.interactions",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: usage,
    components: compactComponents([
      ...inputComponents.slice(0, 1),
      positiveComponent("input_cache_read_tokens", cacheRead, "token", cacheReadSource),
      ...inputComponents.slice(1),
      ...outputComponents.slice(0, 1),
      positiveComponent("output_reasoning_tokens", thoughts, "token", `${sourceRoot}.total_thought_tokens`),
      ...outputComponents.slice(1),
      ...googleInteractionsGroundingComponents(usage, sourceRoot)
    ])
  });
  const serviceTier = googleInteractionsServiceTier(response, usage);
  if (serviceTier) ledger.context = { service_tier: serviceTier };
  return ledger;
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

function bedrockInvokeModelBody(response) {
  if (!hasOwn(response, "body")) {
    return {
      body: response,
      sourceRoot: "$"
    };
  }
  let body = response.body;
  if (body && typeof body === "object" && !(body instanceof Uint8Array)) {
    return {
      body,
      sourceRoot: "$.body"
    };
  }
  if (body instanceof Uint8Array) {
    body = new TextDecoder().decode(body);
  }
  if (typeof body === "string") {
    try {
      const decoded = JSON.parse(body);
      if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) {
        return {
          body: decoded,
          sourceRoot: "$.body"
        };
      }
    } catch {
      return {
        body: {},
        sourceRoot: "$.body"
      };
    }
  }
  return {
    body: {},
    sourceRoot: "$.body"
  };
}

export function extractBedrockInvokeModelUsage(response, options = {}) {
  const { body, sourceRoot } = bedrockInvokeModelBody(response);
  const usage = body.usage || {};
  const input = usage.input_tokens || 0;
  const cacheWrite = usage.cache_creation_input_tokens || 0;
  const cacheWrite1h = usage.cache_creation_input_tokens_1h || 0;
  const cacheRead = usage.cache_read_input_tokens || 0;
  const output = usage.output_tokens || 0;
  const returnedModel = response.modelId || response.model_id || options.model || body.model;

  return baseUsageLedger({
    provider: options.provider || "bedrock",
    surface: options.surface || "aws.bedrock.invoke_model",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", input, "token", `${sourceRoot}.usage.input_tokens`),
      positiveComponent("input_cache_write_tokens", cacheWrite - cacheWrite1h, "token", `${sourceRoot}.usage.cache_creation_input_tokens`),
      positiveComponent("input_cache_write_1h_tokens", cacheWrite1h, "token", `${sourceRoot}.usage.cache_creation_input_tokens_1h`),
      positiveComponent("input_cache_read_tokens", cacheRead, "token", `${sourceRoot}.usage.cache_read_input_tokens`),
      positiveComponent("output_text_tokens", output, "token", `${sourceRoot}.usage.output_tokens`)
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

export function extractCohereRerankUsage(response, options = {}) {
  const meta = response.meta && typeof response.meta === "object" ? response.meta : {};
  const billedUnits = meta.billed_units || {};
  const returnedModel = response.model || options.model;

  return baseUsageLedger({
    provider: options.provider || "cohere",
    surface: options.surface || "cohere.rerank",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: meta,
    components: compactComponents([
      positiveComponent("rerank_search_units", billedUnits.search_units || 0, "search", "$.meta.billed_units.search_units")
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

function vercelAISDKRawUsagePayloads(response, usage) {
  if (Array.isArray(response.steps)) {
    const stepRawUsages = response.steps
      .map((step) => step?.usage?.raw)
      .filter((rawUsage) => rawUsage && typeof rawUsage === "object");
    if (stepRawUsages.length > 0) {
      return stepRawUsages;
    }
  }
  if (usage.raw && typeof usage.raw === "object") {
    return [usage.raw];
  }
  for (const candidate of [response.usage?.raw, response.totalUsage?.raw, response.finalStep?.usage?.raw]) {
    if (candidate && typeof candidate === "object") {
      return [candidate];
    }
  }
  return [];
}

export function extractVercelAISDKUsage(response, options = {}) {
  const { usage, sourceRoot } = vercelAISDKUsagePayload(response);
  const orchestrationUsage = sumOpenAIResponsesOrchestrationUsage(vercelAISDKRawUsagePayloads(response, usage));
  const inputDetails = usage.inputTokenDetails || {};
  const outputDetails = usage.outputTokenDetails || {};
  const baseCacheRead = inputDetails.cacheReadTokens ?? usage.cachedInputTokens ?? 0;
  const cacheRead = addDecimal(baseCacheRead, orchestrationUsage.cachedInput);
  const cacheWrite = inputDetails.cacheWriteTokens || 0;
  const inputTokens = usage.inputTokens || 0;
  const baseUncached = inputDetails.noCacheTokens ?? subtractDecimal(subtractDecimal(inputTokens, baseCacheRead), cacheWrite);
  const uncached = addDecimal(baseUncached, subtractDecimal(orchestrationUsage.input, orchestrationUsage.cachedInput));
  const outputTokens = usage.outputTokens || 0;
  const reasoning = outputDetails.reasoningTokens ?? usage.reasoningTokens ?? 0;
  const baseTextTokens = outputDetails.textTokens ?? subtractDecimal(outputTokens, reasoning);
  const textTokens = addDecimal(baseTextTokens, orchestrationUsage.output);
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

function haystackUsagePayload(response) {
  const replies = response.replies || [];
  if (replies.length) {
    const reply = replies[0] || {};
    const metadata = reply._meta || reply.meta || {};
    if (metadata && typeof metadata === "object") {
      return {
        usage: metadata.usage || {},
        metadata,
        sourceRoot: "$.replies[0]._meta.usage"
      };
    }
  }
  const meta = response.meta;
  if (Array.isArray(meta) && meta.length) {
    const metadata = meta[0] || {};
    return {
      usage: metadata.usage || {},
      metadata,
      sourceRoot: "$.meta[0].usage"
    };
  }
  if (meta && typeof meta === "object") {
    return {
      usage: meta.usage || {},
      metadata: meta,
      sourceRoot: "$.meta.usage"
    };
  }
  return {
    usage: response.usage || {},
    metadata: response,
    sourceRoot: "$.usage"
  };
}

export function extractHaystackGeneratorUsage(response, options = {}) {
  const { usage, metadata, sourceRoot } = haystackUsagePayload(response);
  const cachedInput = openAICompatibleCachedInput(usage);
  const reasoning = openAICompatibleReasoningOutput(usage);
  const prompt = usage.prompt_tokens ?? ((usage.prompt_cache_hit_tokens || 0) + (usage.prompt_cache_miss_tokens || 0));
  const completion = usage.completion_tokens || 0;
  const returnedModel = metadata.model || response.model || options.model;

  return baseUsageLedger({
    provider: options.provider || "unknown",
    surface: options.surface || "framework.haystack.generator",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", prompt - cachedInput.value, "token", `${sourceRoot}.prompt_tokens`),
      positiveComponent("input_cache_read_tokens", cachedInput.value, "token", cachedInput.sourcePath.replace("$.usage", sourceRoot)),
      positiveComponent("output_text_tokens", completion - reasoning.value, "token", `${sourceRoot}.completion_tokens`),
      positiveComponent("output_reasoning_tokens", reasoning.value, "token", reasoning.sourcePath.replace("$.usage", sourceRoot))
    ])
  });
}

export function extractLiteLLMProxyResponseUsage(response, options = {}) {
  const hidden = response._hidden_params || response.hidden_params || {};
  return extractOpenAICompatibleChatCompletionsUsage(response, {
    ...options,
    provider: options.provider || hidden.custom_llm_provider || hidden.litellm_provider
  });
}

function ag2UsageSummaryPayload(response, options = {}) {
  const mode = options.ag2_usage_mode || options.usage_mode || "actual";
  if (response.usage_excluding_cached_inference || response.usage_including_cached_inference) {
    if (["total", "including_cached", "usage_including_cached_inference"].includes(mode)) {
      return {
        summary: response.usage_including_cached_inference || {},
        mode: "usage_including_cached_inference"
      };
    }
    return {
      summary: response.usage_excluding_cached_inference || {},
      mode: "usage_excluding_cached_inference"
    };
  }
  return {
    summary: response,
    mode: String(mode)
  };
}

function ag2ModelUsage(summary, requestedModel) {
  if (requestedModel && summary[requestedModel] && typeof summary[requestedModel] === "object") {
    return {
      model: requestedModel,
      usage: summary[requestedModel]
    };
  }
  for (const [key, value] of Object.entries(summary)) {
    if (key !== "total_cost" && value && typeof value === "object") {
      return {
        model: key,
        usage: value
      };
    }
  }
  return {
    model: requestedModel || "unknown",
    usage: {}
  };
}

export function extractAG2UsageSummaryUsage(response, options = {}) {
  const { summary, mode } = ag2UsageSummaryPayload(response, options);
  const { model, usage } = ag2ModelUsage(summary, options.model);
  const promptTokens = usage.prompt_tokens || 0;
  const completionTokens = usage.completion_tokens || 0;

  return baseUsageLedger({
    provider: options.provider || "unknown",
    surface: options.surface || "framework.ag2.usage_summary",
    requestedModel: options.model || model,
    returnedModel: model,
    rawUsage: {
      mode,
      summary,
      model_usage: usage
    },
    components: compactComponents([
      positiveComponent("input_uncached_tokens", promptTokens, "token", `$.${mode}.${model}.prompt_tokens`),
      positiveComponent("output_text_tokens", completionTokens, "token", `$.${mode}.${model}.completion_tokens`)
    ])
  });
}

function firstPresent(object, keys, defaultValue = 0) {
  for (const key of keys) {
    if (object && object[key] !== undefined && object[key] !== null) {
      return object[key];
    }
  }
  return defaultValue;
}

function nestedObject(object, keys) {
  for (const key of keys) {
    if (object && object[key] && typeof object[key] === "object") {
      return object[key];
    }
  }
  return {};
}

function openAIAgentsUsagePayload(response) {
  if (response.usage && typeof response.usage === "object") {
    return { usage: response.usage, sourceRoot: "$.usage", sourceRootValue: response };
  }
  for (const rootKey of ["context_wrapper", "context"]) {
    const root = response[rootKey];
    if (root && typeof root === "object" && root.usage && typeof root.usage === "object") {
      return { usage: root.usage, sourceRoot: `$.${rootKey}.usage`, sourceRootValue: root };
    }
  }
  return { usage: response, sourceRoot: "$", sourceRootValue: response };
}

export function extractOpenAIAgentsUsage(response, options = {}) {
  const { usage, sourceRoot, sourceRootValue } = openAIAgentsUsagePayload(response);
  const inputDetails = nestedObject(usage, ["input_tokens_details"]);
  const cachedInput = inputDetails.cached_tokens || 0;
  const cacheWrite = inputDetails.cache_write_tokens || 0;
  const reasoning = nestedObject(usage, ["output_tokens_details"]).reasoning_tokens || 0;
  const inputTokens = usage.input_tokens || 0;
  const outputTokens = usage.output_tokens || 0;
  const returnedModel = usage.model || sourceRootValue.model || response.model || options.model;
  const provider = options.provider || "openai";
  const context = usageContextFromOptions(sourceRootValue, provider, options);

  return baseUsageLedger({
    provider,
    surface: options.surface || "openai.responses",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: usage,
    context,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", inputTokens - cachedInput - cacheWrite, "token", `${sourceRoot}.input_tokens`),
      positiveComponent("input_cache_read_tokens", cachedInput, "token", `${sourceRoot}.input_tokens_details.cached_tokens`),
      positiveComponent("input_cache_write_tokens", cacheWrite, "token", `${sourceRoot}.input_tokens_details.cache_write_tokens`),
      positiveComponent("output_text_tokens", outputTokens - reasoning, "token", `${sourceRoot}.output_tokens`),
      positiveComponent("output_reasoning_tokens", reasoning, "token", `${sourceRoot}.output_tokens_details.reasoning_tokens`)
    ])
  });
}

function langSmithUsagePayload(response) {
  if (response.usage_metadata && typeof response.usage_metadata === "object") {
    return { usage: response.usage_metadata, sourceRoot: "$.usage_metadata" };
  }
  if (response.usageMetadata && typeof response.usageMetadata === "object") {
    return { usage: response.usageMetadata, sourceRoot: "$.usageMetadata" };
  }
  const outputs = response.outputs || {};
  if (outputs.usage_metadata && typeof outputs.usage_metadata === "object") {
    return { usage: outputs.usage_metadata, sourceRoot: "$.outputs.usage_metadata" };
  }
  if (outputs.usageMetadata && typeof outputs.usageMetadata === "object") {
    return { usage: outputs.usageMetadata, sourceRoot: "$.outputs.usageMetadata" };
  }
  if (outputs.llm_output && outputs.llm_output.usage && typeof outputs.llm_output.usage === "object") {
    return { usage: outputs.llm_output.usage, sourceRoot: "$.outputs.llm_output.usage" };
  }
  if (["input_tokens", "inputTokens", "prompt_tokens", "promptTokens"].some((key) => hasOwn(response, key))) {
    return { usage: response, sourceRoot: "$" };
  }
  return { usage: {}, sourceRoot: "$.usage_metadata" };
}

function langSmithModel(response, usage, options) {
  const serializedKwargs = response.serialized?.kwargs || {};
  return usage.model
    || usage.model_name
    || response.model
    || response.model_name
    || serializedKwargs.model
    || serializedKwargs.model_name
    || options.model;
}

export function extractLangSmithRunUsage(response, options = {}) {
  const { usage, sourceRoot } = langSmithUsagePayload(response);
  const inputDetails = nestedObject(usage, ["input_token_details", "inputTokenDetails"]);
  const outputDetails = nestedObject(usage, ["output_token_details", "outputTokenDetails"]);
  const cacheRead = firstPresent(inputDetails, ["cache_read", "cacheReadTokens", "cache_read_tokens"]);
  const cacheWrite = firstPresent(inputDetails, ["cache_creation", "cacheWriteTokens", "cache_write_tokens"]);
  const inputTokens = firstPresent(usage, ["input_tokens", "inputTokens", "prompt_tokens", "promptTokens"]);
  const outputTokens = firstPresent(usage, ["output_tokens", "outputTokens", "completion_tokens", "completionTokens"]);
  const reasoning = firstPresent(outputDetails, ["reasoning", "reasoningTokens", "reasoning_tokens"]);
  const returnedModel = langSmithModel(response, usage, options);

  return baseUsageLedger({
    provider: options.provider || "unknown",
    surface: options.surface || "framework.langsmith.run_usage",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage: usage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", inputTokens - cacheRead - cacheWrite, "token", `${sourceRoot}.input_tokens`),
      positiveComponent("input_cache_read_tokens", cacheRead, "token", `${sourceRoot}.input_token_details.cache_read`),
      positiveComponent("input_cache_write_tokens", cacheWrite, "token", `${sourceRoot}.input_token_details.cache_creation`),
      positiveComponent("output_text_tokens", outputTokens - reasoning, "token", `${sourceRoot}.output_tokens`),
      positiveComponent("output_reasoning_tokens", reasoning, "token", `${sourceRoot}.output_token_details.reasoning`)
    ])
  });
}

function semanticKernelUsagePayload(response) {
  for (const key of ["usage", "token_usage", "tokenUsage"]) {
    if (response[key] && typeof response[key] === "object") {
      return { usage: response[key], sourceRoot: `$.${key}` };
    }
  }
  const metadata = response.metadata || {};
  for (const key of ["usage", "token_usage", "tokenUsage"]) {
    if (metadata[key] && typeof metadata[key] === "object") {
      return { usage: metadata[key], sourceRoot: `$.metadata.${key}` };
    }
  }
  return { usage: response, sourceRoot: "$" };
}

export function extractSemanticKernelTelemetryUsage(response, options = {}) {
  const { usage, sourceRoot } = semanticKernelUsagePayload(response);
  const inputTokens = firstPresent(usage, ["prompt_tokens", "promptTokens", "input_tokens", "inputTokens"]);
  const outputTokens = firstPresent(usage, ["completion_tokens", "completionTokens", "output_tokens", "outputTokens"]);
  const metadata = response.metadata || {};
  const returnedModel = usage.model || metadata.model || response.model || options.model;
  const rawUsage = { ...usage };
  for (const key of ["plugin_name", "function_name", "pluginName", "functionName"]) {
    if (hasOwn(response, key)) rawUsage[key] = response[key];
  }

  return baseUsageLedger({
    provider: options.provider || "unknown",
    surface: options.surface || "framework.semantic_kernel.telemetry",
    requestedModel: options.model || returnedModel,
    returnedModel,
    rawUsage,
    components: compactComponents([
      positiveComponent("input_uncached_tokens", inputTokens, "token", `${sourceRoot}.prompt_tokens`),
      positiveComponent("output_text_tokens", outputTokens, "token", `${sourceRoot}.completion_tokens`)
    ])
  });
}

function openRouterSDKResponsePayload(response) {
  if (response.response && response.response.usage && typeof response.response.usage === "object") {
    return response.response;
  }
  return response;
}

export function extractOpenRouterSDKResponseUsage(response, options = {}) {
  const payload = openRouterSDKResponsePayload(response);
  const usage = payload.usage || {};
  if (["inputTokens", "outputTokens", "cachedTokens", "reasoningTokens"].some((key) => hasOwn(usage, key))) {
    const inputTokens = firstPresent(usage, ["inputTokens", "promptTokens"]);
    const cachedInput = firstPresent(usage, ["cachedTokens", "cachedInputTokens"]);
    const outputTokens = firstPresent(usage, ["outputTokens", "completionTokens"]);
    const reasoning = firstPresent(usage, ["reasoningTokens"]);
    return baseUsageLedger({
      provider: options.provider || "openrouter",
      surface: options.surface || "openrouter.chat_completions",
      requestedModel: options.model || payload.model,
      returnedModel: payload.model,
      rawUsage: usage,
      components: compactComponents([
        positiveComponent("input_uncached_tokens", inputTokens - cachedInput, "token", "$.usage.inputTokens"),
        positiveComponent("input_cache_read_tokens", cachedInput, "token", "$.usage.cachedTokens"),
        positiveComponent("output_text_tokens", outputTokens - reasoning, "token", "$.usage.outputTokens"),
        positiveComponent("output_reasoning_tokens", reasoning, "token", "$.usage.reasoningTokens")
      ])
    });
  }
  return extractOpenAICompatibleChatCompletionsUsage(payload, {
    provider: "openrouter",
    surface: "openrouter.chat_completions",
    ...options
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
  if (adapter === "vercel_ai_sdk.stream_text") {
    return extractVercelAISDKUsage(response, options);
  }
  if (adapter === "vercel_ai_sdk.stream_transcribe") {
    return extractOpenAIAudioTranscriptionUsage(response, {
      provider: "openai",
      surface: "openai.audio_transcriptions",
      ...options
    });
  }
  if (adapter === "llamaindex.token_counter") {
    return extractLlamaIndexTokenCounterUsage(response, options);
  }
  if (adapter === "haystack.generator_result") {
    return extractHaystackGeneratorUsage(response, options);
  }
  if (adapter === "litellm.proxy_response") {
    return extractLiteLLMProxyResponseUsage(response, options);
  }
  if (adapter === "ag2.usage_summary") {
    return extractAG2UsageSummaryUsage(response, options);
  }
  if (adapter === "openai_agents.usage") {
    return extractOpenAIAgentsUsage(response, options);
  }
  if (adapter === "langsmith.run_usage") {
    return extractLangSmithRunUsage(response, options);
  }
  if (adapter === "semantic_kernel.telemetry") {
    return extractSemanticKernelTelemetryUsage(response, options);
  }
  if (adapter === "openrouter.sdk_response") {
    return extractOpenRouterSDKResponseUsage(response, options);
  }

  const surface = options.surface;
  if (surface === "openai.responses" || surface === "xai.responses" || surface === "meta.responses") {
    return extractOpenAIResponsesUsage(response, options);
  }
  if (surface === "openai.embeddings") {
    return extractOpenAIEmbeddingsUsage(response, options);
  }
  if (surface === "openai.audio_transcriptions") {
    return extractOpenAIAudioTranscriptionUsage(response, options);
  }
  if (surface === "openai.images") {
    return extractOpenAIImagesUsage(response, options);
  }
  if (surface === "openai.usage.images") {
    return extractOpenAIUsageImagesUsage(response, options);
  }
  if (surface === "openai.usage.completions") {
    return extractOpenAIUsageCompletionsUsage(response, options);
  }
  if (surface === "openai.usage.audio_speeches") {
    return extractOpenAIUsageAudioSpeechesUsage(response, options);
  }
  if (surface === "openai.usage.audio_transcriptions") {
    return extractOpenAIUsageAudioTranscriptionsUsage(response, options);
  }
  if (surface === "openai.usage.embeddings") {
    return extractOpenAIUsageEmbeddingsUsage(response, options);
  }
  if (surface === "openai.vector_stores") {
    return extractOpenAIVectorStoreStorageUsage(response, options);
  }
  if (surface === "openai.usage.code_interpreter_sessions") {
    return extractOpenAIUsageCodeInterpreterSessionsUsage(response, options);
  }
  if (surface === "openai.chat_completions") {
    return extractOpenAIChatCompletionsUsage(response, options);
  }
  if (hasOwn(OPENAI_COMPATIBLE_CHAT_PROVIDERS, surface)) {
    return extractOpenAICompatibleChatCompletionsUsage(response, options);
  }
  if (surface === "anthropic.messages" || surface === "minimax.messages") {
    return extractAnthropicMessagesUsage(response, options);
  }
  if (surface === "google.gemini.generate_content" || surface === "vertex.gemini.generate_content") {
    return extractGeminiGenerateContentUsage(response, options);
  }
  if (surface === "google.gemini.live") {
    return extractGeminiLiveUsage(response, options);
  }
  if (surface === "google.gemini.interactions") {
    return extractGoogleInteractionsUsage(response, options);
  }
  if (surface === "aws.bedrock.converse") {
    return extractBedrockConverseUsage(response, options);
  }
  if (surface === "aws.bedrock.invoke_model") {
    return extractBedrockInvokeModelUsage(response, options);
  }
  if (surface === "cohere.chat") {
    return extractCohereChatUsage(response, options);
  }
  if (surface === "cohere.rerank") {
    return extractCohereRerankUsage(response, options);
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
        message: `Unsupported surface: ${surface}.`,
        metadata: {
          provider,
          surface,
          model
        }
      }
    ]
  };
}

function llmPricesIsHistorical(data) {
  return (data.prices || []).some((price) => (
    price && typeof price === "object" && ("from_date" in price || "to_date" in price)
  ));
}

export function priceCardsFromLlmPrices(data, options = {}) {
  const retrievedAt = options.retrievedAt || options.retrieved_at || `${data.updated_at || "1970-01-01"}T00:00:00Z`;
  const defaultUrl = llmPricesIsHistorical(data)
    ? "https://www.llm-prices.com/historical-v1.json"
    : "https://www.llm-prices.com/current-v1.json";
  const sourceUrl = options.sourceUrl || options.source_url || defaultUrl;
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

function modelsDevTiers(cost) {
  if (!cost || typeof cost !== "object") {
    return [];
  }
  const rawTiers = [];
  for (const tier of cost.tiers || []) {
    if (!tier || typeof tier !== "object") {
      continue;
    }
    const tierInfo = tier.tier && typeof tier.tier === "object" ? tier.tier : {};
    if (tierInfo.type === "context" && tierInfo.size !== undefined && tierInfo.size !== null) {
      rawTiers.push({ cost: tier, size: tierInfo.size });
    }
  }
  rawTiers.sort((left, right) => Number(left.size) - Number(right.size));
  const baseConditions = {};
  if (rawTiers.length > 0) {
    baseConditions.max_total_input_tokens = subtractDecimal(rawTiers[0].size, "1");
  }
  const tiers = [{ cost, conditions: baseConditions }];
  rawTiers.forEach((tier, index) => {
    const conditions = { min_total_input_tokens: numberString(tier.size) };
    if (index + 1 < rawTiers.length) {
      conditions.max_total_input_tokens = subtractDecimal(rawTiers[index + 1].size, "1");
    }
    tiers.push({ cost: tier.cost, conditions });
  });
  return tiers;
}

function addModelsDevCostComponents(components, cost, conditions) {
  const extra = Object.keys(conditions).length > 0 ? { conditions } : {};
  addPriceComponent(components, "input_uncached_tokens", "token", cost.input, "1000000", extra);
  addPriceComponent(components, "output_text_tokens", "token", cost.output, "1000000", extra);
  addPriceComponent(components, "output_reasoning_tokens", "token", cost.reasoning, "1000000", extra);
  addPriceComponent(components, "input_cache_read_tokens", "token", cost.cache_read, "1000000", extra);
  addPriceComponent(components, "input_cache_write_tokens", "token", cost.cache_write, "1000000", extra);
  addPriceComponent(components, "input_audio_tokens", "token", cost.input_audio, "1000000", extra);
  addPriceComponent(components, "output_audio_tokens", "token", cost.output_audio, "1000000", extra);
}

export function priceCardsFromModelsDev(data, options = {}) {
  const retrievedAt = options.retrievedAt || options.retrieved_at || `${data.updated_at || "1970-01-01"}T00:00:00Z`;
  const sourceUrl = options.sourceUrl || options.source_url || "https://models.dev/api.json";
  return Object.entries(data || {}).flatMap(([providerId, provider]) => {
    if (!provider || typeof provider !== "object") {
      return [];
    }
    return Object.entries(provider.models || {}).flatMap(([modelId, model]) => {
      if (!model || typeof model !== "object") {
        return [];
      }
      const components = [];
      for (const tier of modelsDevTiers(model.cost)) {
        addModelsDevCostComponents(components, tier.cost, tier.conditions);
      }
      if (components.length === 0) {
        return [];
      }
      const aliases = [model.name, `${providerId}/${modelId}`].filter((alias) => alias && alias !== modelId);
      return [{
        schema_version: "0.1",
        id: `${providerId}:${modelId}:models-dev`,
        provider: providerId,
        model: modelId,
        aliases,
        components,
        source: {
          name: "models.dev",
          url: sourceUrl,
          retrieved_at: retrievedAt,
          license: "MIT"
        },
        metadata: {
          models_dev: {
            provider_name: provider.name,
            family: model.family,
            limit: model.limit,
            modalities: model.modalities,
            reasoning: model.reasoning,
            tool_call: model.tool_call,
            status: model.status,
            release_date: model.release_date,
            last_updated: model.last_updated
          }
        }
      }];
    });
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

function normalizePriceCard(card) {
  const normalized = { ...card };
  const schedule = normalizeBillingSchedule(normalized.billing_schedule || normalized.billingSchedule);
  if (schedule) {
    normalized.billing_schedule = schedule;
    delete normalized.billingSchedule;
  }
  return normalized;
}

function canonicalPriceCards(rawCards) {
  return Array.isArray(rawCards)
    ? rawCards.filter((card) => card && typeof card === "object").map((card) => normalizePriceCard(card))
    : [];
}

function sourceCachePriceCards(entry) {
  for (const key of ["price_cards", "priceCards", "cards"]) {
    if (Array.isArray(entry[key])) {
      return canonicalPriceCards(entry[key]);
    }
  }
  return [];
}

function sourceCacheSource(entry) {
  const source = entry.source && typeof entry.source === "object" ? entry.source : {};
  const sourceType = entry.type || entry.source_type || entry.sourceType;
  const info = { name: entry.name || source.name || sourceType || "source-cache" };
  const url = entry.url || source.url;
  if (url) info.url = url;
  const retrievedAt = entry.retrieved_at || entry.retrievedAt || source.retrieved_at || source.retrievedAt;
  if (retrievedAt) info.retrieved_at = retrievedAt;
  const version = entry.version || source.version;
  if (version) info.version = version;
  const license = entry.license || source.license;
  if (license) info.license = license;
  return info;
}

function sourceCacheMetadata(data, entry, cardCount) {
  const metadata = { card_count: cardCount };
  const fields = [
    ["generated_at", ["generated_at", "generatedAt"]],
    ["checksum", ["checksum", "sha256"]],
    ["source_type", ["type", "source_type", "sourceType"]]
  ];
  for (const [outputKey, inputKeys] of fields) {
    for (const inputKey of inputKeys) {
      const value = entry[inputKey] ?? data[inputKey];
      if (value) {
        metadata[outputKey] = value;
        break;
      }
    }
  }
  return metadata;
}

export function priceCardsFromSourceCache(data) {
  if (!data || typeof data !== "object") {
    return [];
  }
  const entries = Array.isArray(data.sources) ? data.sources : [data];
  return entries.flatMap((entry) => {
    if (!entry || typeof entry !== "object") {
      return [];
    }
    const rawCards = sourceCachePriceCards(entry);
    const source = sourceCacheSource(entry);
    const cacheMetadata = sourceCacheMetadata(data, entry, rawCards.length);
    return rawCards.map((rawCard) => ({
      ...rawCard,
      schema_version: rawCard.schema_version || "0.1",
      source: rawCard.source || source,
      metadata: {
        ...(rawCard.metadata && typeof rawCard.metadata === "object" ? rawCard.metadata : {}),
        source_cache: cacheMetadata
      }
    }));
  });
}

export function priceCardsFromJSONFile(filePath, options = {}) {
  const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
  const sourceType = options.sourceType || options.source_type || "user-pricing";
  const adapterOptions = {
    ...options,
    sourceUrl: options.sourceUrl || options.source_url || pathToFileURL(path.resolve(filePath)).href,
    source_url: options.source_url || options.sourceUrl || pathToFileURL(path.resolve(filePath)).href
  };
  if (sourceType === "llm-prices") return priceCardsFromLlmPrices(data, adapterOptions);
  if (sourceType === "litellm") return priceCardsFromLiteLLM(data, adapterOptions);
  if (sourceType === "openrouter-models") return priceCardsFromOpenRouterModels(data, adapterOptions);
  if (sourceType === "models-dev") return priceCardsFromModelsDev(data, adapterOptions);
  if (sourceType === "official-snapshot") return priceCardsFromOfficialSnapshot(data, adapterOptions);
  if (sourceType === "portkey") return priceCardsFromPortkey(data, adapterOptions);
  if (sourceType === "source-cache") return priceCardsFromSourceCache(data, adapterOptions);
  if (sourceType === "user-pricing") return priceCardsFromUserPricing(data, adapterOptions);
  if (sourceType === "helicone") return priceCardsFromHelicone(data, adapterOptions);
  throw new Error(`Unsupported JSON price source type: ${sourceType}`);
}

function stripYAMLComment(line) {
  let quote = null;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if ((char === "'" || char === "\"") && !quote) quote = char;
    else if (char === quote) quote = null;
    if (char === "#" && !quote && (index === 0 || /\s/.test(line[index - 1]))) {
      return line.slice(0, index).trimEnd();
    }
  }
  return line.trimEnd();
}

function yamlScalar(value) {
  const trimmed = value.trim();
  if (["", "null", "Null", "NULL", "~"].includes(trimmed)) return null;
  if (["true", "True", "TRUE"].includes(trimmed)) return true;
  if (["false", "False", "FALSE"].includes(trimmed)) return false;
  if ((trimmed.startsWith("\"") && trimmed.endsWith("\"")) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.slice(1, -1);
  }
  if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
    const inner = trimmed.slice(1, -1).trim();
    if (!inner) return [];
    return inner.split(",").map((part) => yamlScalar(part.trim()));
  }
  return trimmed;
}

function yamlKeyValue(content) {
  const index = content.indexOf(":");
  if (index < 0) {
    throw new Error(`Unsupported YAML line: ${content}`);
  }
  return [content.slice(0, index).trim(), content.slice(index + 1).trim()];
}

function yamlLines(text) {
  return text.split(/\r?\n/).flatMap((line) => {
    const cleaned = stripYAMLComment(line);
    if (!cleaned.trim()) return [];
    const indent = cleaned.length - cleaned.trimStart().length;
    return [{ indent, content: cleaned.trim() }];
  });
}

function parseYAMLBlock(lines, start, indent) {
  let index = start;
  if (index >= lines.length || lines[index].indent < indent) {
    return [{}, index];
  }
  if (lines[index].content.startsWith("- ")) {
    const values = [];
    while (index < lines.length && lines[index].indent === indent && lines[index].content.startsWith("- ")) {
      const rest = lines[index].content.slice(2).trim();
      index += 1;
      if (!rest) {
        const [value, next] = parseYAMLBlock(lines, index, indent + 2);
        values.push(value);
        index = next;
      } else if (rest.includes(":")) {
        const [key, rawValue] = yamlKeyValue(rest);
        const item = {};
        if (rawValue) {
          item[key] = yamlScalar(rawValue);
        } else {
          const [value, next] = parseYAMLBlock(lines, index, indent + 2);
          item[key] = value;
          index = next;
        }
        if (index < lines.length && lines[index].indent >= indent + 2) {
          const [extra, next] = parseYAMLBlock(lines, index, indent + 2);
          if (extra && typeof extra === "object" && !Array.isArray(extra)) Object.assign(item, extra);
          index = next;
        }
        values.push(item);
      } else {
        values.push(yamlScalar(rest));
      }
    }
    return [values, index];
  }
  const mapping = {};
  while (index < lines.length) {
    const line = lines[index];
    if (line.indent < indent) break;
    if (line.indent > indent || line.content.startsWith("- ")) break;
    const [key, rawValue] = yamlKeyValue(line.content);
    index += 1;
    if (rawValue) {
      mapping[key] = yamlScalar(rawValue);
    } else {
      const [value, next] = parseYAMLBlock(lines, index, indent + 2);
      mapping[key] = value;
      index = next;
    }
  }
  return [mapping, index];
}

function parseSimpleYAML(text) {
  const lines = yamlLines(text);
  if (lines.length === 0) return {};
  const [data, index] = parseYAMLBlock(lines, 0, lines[0].indent);
  if (index !== lines.length) {
    throw new Error("Unsupported YAML structure");
  }
  return data;
}

function priceCardsFromSourceData(data, sourceType, options = {}) {
  if (sourceType === "llm-prices") return priceCardsFromLlmPrices(data, options);
  if (sourceType === "litellm") return priceCardsFromLiteLLM(data, options);
  if (sourceType === "openrouter-models") return priceCardsFromOpenRouterModels(data, options);
  if (sourceType === "models-dev") return priceCardsFromModelsDev(data, options);
  if (sourceType === "official-snapshot") return priceCardsFromOfficialSnapshot(data, options);
  if (sourceType === "portkey") return priceCardsFromPortkey(data, options);
  if (sourceType === "source-cache") return priceCardsFromSourceCache(data, options);
  if (sourceType === "user-pricing") return priceCardsFromUserPricing(data, options);
  if (sourceType === "helicone") return priceCardsFromHelicone(data, options);
  throw new Error(`Unsupported price source type: ${sourceType}`);
}

export function priceCardsFromYAMLFile(filePath, options = {}) {
  const data = parseSimpleYAML(fs.readFileSync(filePath, "utf8"));
  const sourceType = options.sourceType || options.source_type || "user-pricing";
  const adapterOptions = {
    ...options,
    sourceUrl: options.sourceUrl || options.source_url || pathToFileURL(path.resolve(filePath)).href,
    source_url: options.source_url || options.sourceUrl || pathToFileURL(path.resolve(filePath)).href
  };
  return priceCardsFromSourceData(data, sourceType, adapterOptions);
}

function addOfficialSnapshotComponent(components, row, componentName, unit, keys, per) {
  addPriceComponent(components, componentName, unit, componentAmount(row, keys), per);
}

export function priceCardsFromOfficialSnapshot(data, options = {}) {
  if (!data || typeof data !== "object") {
    return [];
  }
  if (data.price_cards) {
    return canonicalPriceCards(data.price_cards);
  }
  if (data.priceCards) {
    return canonicalPriceCards(data.priceCards);
  }
  const source = sourceInfo(data, "official-snapshot", "file://official-pricing-snapshot", options);
  const providerDefault = data.provider || options.provider || "unknown";
  const surfaceDefault = data.surface || options.surface;
  const perDefault = numberString(data.per || "1000000");
  const scheduleDefault = normalizeBillingSchedule(data.billing_schedule || data.billingSchedule);
  const toolPriceDefaults = data.tool_prices && typeof data.tool_prices === "object"
    ? data.tool_prices
    : data.toolPrices && typeof data.toolPrices === "object"
      ? data.toolPrices
      : {};
  const rows = data.rows || data.models || [];
  return rows.flatMap((row) => {
    if (!row || typeof row !== "object") return [];
    const model = row.model || row.id;
    const provider = row.provider || providerDefault;
    if (!model || !provider) return [];
    const per = numberString(row.per || perDefault);
    const rowToolPrices = row.tool_prices && typeof row.tool_prices === "object"
      ? row.tool_prices
      : row.toolPrices && typeof row.toolPrices === "object"
        ? row.toolPrices
        : {};
    const pricingRow = {
      ...toolPriceDefaults,
      ...rowToolPrices,
      ...row
    };
    const components = [];
    for (const rawComponent of row.components || []) {
      if (!rawComponent || typeof rawComponent !== "object") continue;
      const amount = rawComponent.amount ?? (rawComponent.price && rawComponent.price.amount);
      const extra = {};
      if (rawComponent.conditions && typeof rawComponent.conditions === "object") {
        extra.conditions = rawComponent.conditions;
      }
      if (typeof rawComponent.discount_eligible === "boolean") {
        extra.discount_eligible = rawComponent.discount_eligible;
      }
      if (typeof rawComponent.notes === "string") {
        extra.notes = rawComponent.notes;
      }
      addPriceComponent(
        components,
        rawComponent.usage_component,
        rawComponent.unit || "token",
        amount,
        numberString(rawComponent.per || (rawComponent.price && rawComponent.price.per) || per),
        extra
      );
    }
    addOfficialSnapshotComponent(components, pricingRow, "input_uncached_tokens", "token", ["input", "prompt", "input_uncached"], per);
    addOfficialSnapshotComponent(components, pricingRow, "input_cache_read_tokens", "token", ["cache_read", "cached_input", "input_cache_read"], per);
    addOfficialSnapshotComponent(components, pricingRow, "input_cache_write_tokens", "token", ["cache_write", "input_cache_write"], per);
    addOfficialSnapshotComponent(components, pricingRow, "input_cache_write_1h_tokens", "token", ["cache_write_1h", "input_cache_write_1h"], per);
    addOfficialSnapshotComponent(components, pricingRow, "output_text_tokens", "token", ["output", "completion", "output_text"], per);
    addOfficialSnapshotComponent(components, pricingRow, "output_reasoning_tokens", "token", ["reasoning", "thinking", "output_reasoning"], per);
    addOfficialSnapshotComponent(components, pricingRow, "input_audio_tokens", "token", ["input_audio", "audio_input"], per);
    addOfficialSnapshotComponent(components, pricingRow, "output_audio_tokens", "token", ["output_audio", "audio_output"], per);
    addOfficialSnapshotComponent(components, pricingRow, "request_units", "request", ["request", "per_request"], "1");
    addOfficialSnapshotComponent(components, pricingRow, "web_search_units", "search", ["web_search", "search"], "1");
    addOfficialSnapshotComponent(components, pricingRow, "x_search_units", "search", ["x_search"], "1");
    addOfficialSnapshotComponent(components, pricingRow, "file_search_units", "call", ["file_search", "collections_search"], "1");
    addOfficialSnapshotComponent(components, pricingRow, "code_interpreter_call_units", "call", ["code_interpreter_call", "code_interpreter", "code_execution"], "1");
    addOfficialSnapshotComponent(components, pricingRow, "attachment_search_units", "call", ["attachment_search"], "1");
    if (components.length === 0) return [];
    const pricingPeriod = row.pricing_period || row.pricingPeriod;
    const defaultCardId = pricingPeriod
      ? `${provider}:${model}:${pricingPeriod}:official-snapshot`
      : `${provider}:${model}:official-snapshot`;
    const card = {
      schema_version: "0.1",
      id: row.price_card_id || row.priceCardId || defaultCardId,
      provider,
      model,
      aliases: row.aliases || [],
      components,
      source,
      metadata: {
        official_snapshot: {
          source_label: row.source_label || row.sourceLabel,
          notes: row.notes,
          capabilities: row.capabilities
        },
        source_capabilities: row.capabilities && typeof row.capabilities === "object" ? row.capabilities : {}
      }
    };
    const surface = row.surface || surfaceDefault;
    if (surface) card.surface = surface;
    if (row.service_tier) card.service_tier = row.service_tier;
    if (row.region) card.region = row.region;
    if (pricingPeriod) card.pricing_period = pricingPeriod;
    const schedule = normalizeBillingSchedule(row.billing_schedule || row.billingSchedule) || scheduleDefault;
    if (schedule) card.billing_schedule = schedule;
    if (row.effective && typeof row.effective === "object") card.effective = row.effective;
    const cards = [card];
    const serviceTierAliases = row.capabilities && Array.isArray(row.capabilities.service_tier_aliases)
      ? row.capabilities.service_tier_aliases
      : [];
    for (const rawAlias of serviceTierAliases) {
      const alias = String(rawAlias || "").trim().toLowerCase();
      if (!alias || alias === card.service_tier) continue;
      const marker = card.service_tier ? `:${card.service_tier}:` : "";
      const aliasId = marker && card.id.includes(marker)
        ? card.id.replace(marker, `:${alias}:`)
        : `${card.id}:${alias}`;
      cards.push({
        ...card,
        id: aliasId,
        service_tier: alias,
        metadata: {
          ...card.metadata,
          service_tier_resolution: {
            independent_card: true,
            currently_equivalent_to: card.service_tier
          }
        }
      });
    }
    return cards;
  });
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
  const pricingPeriodDefault = data.pricing_period || data.pricingPeriod;
  const scheduleDefault = normalizeBillingSchedule(data.billing_schedule || data.billingSchedule);
  const regionDefault = data.region;
  const perDefault = numberString(data.per || "1000000");
  return (data.models || []).flatMap((entry) => {
    if (!entry || typeof entry !== "object") return [];
    if (entry.components && entry.provider && (entry.model || entry.id)) {
      const card = {
        ...entry,
        schema_version: entry.schema_version || "0.1",
        model: entry.model || entry.id,
        source: entry.source || source
      };
      const schedule = normalizeBillingSchedule(card.billing_schedule || card.billingSchedule);
      if (schedule) {
        card.billing_schedule = schedule;
        delete card.billingSchedule;
      }
      return [card];
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
    const pricingPeriod = entry.pricing_period || entry.pricingPeriod || pricingPeriodDefault;
    if (pricingPeriod) card.pricing_period = pricingPeriod;
    const schedule = normalizeBillingSchedule(entry.billing_schedule || entry.billingSchedule) || scheduleDefault;
    if (schedule) card.billing_schedule = schedule;
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

export function inferSurface(response, options = {}) {
  const payload = response && typeof response === "object" ? response : {};
  const provider = String(options.provider || "").toLowerCase();
  const objectType = String(payload.object || payload.type || "").toLowerCase();
  const usage = payload.usage && typeof payload.usage === "object" ? payload.usage : {};
  if ((payload.usageMetadata && typeof payload.usageMetadata === "object") ||
      (payload.usage_metadata && typeof payload.usage_metadata === "object")) {
    return ["vertex", "google-vertex"].includes(provider)
      ? "vertex.gemini.generate_content"
      : "google.gemini.generate_content";
  }
  if (objectType === "message" && (hasOwn(usage, "input_tokens") || hasOwn(usage, "cache_read_input_tokens"))) {
    return provider === "minimax" ? "minimax.messages" : "anthropic.messages";
  }
  if (objectType === "response" || String(payload.id || "").startsWith("resp_") ||
      (hasOwn(payload, "output") && hasOwn(usage, "input_tokens"))) {
    if (provider === "xai") return "xai.responses";
    if (provider === "meta") return "meta.responses";
    return "openai.responses";
  }
  if (objectType === "list" && Array.isArray(payload.data) && hasOwn(usage, "prompt_tokens")) {
    return "openai.embeddings";
  }
  if (Array.isArray(payload.choices) && Object.keys(usage).length > 0) {
    const surfaces = {
      openai: "openai.chat_completions",
      openrouter: "openrouter.chat_completions",
      groq: "groq.chat_completions",
      xai: "xai.chat_completions",
      meta: "meta.chat_completions",
      mistral: "mistral.chat_completions",
      deepseek: "deepseek.chat_completions",
      azure: "azure.openai.chat_completions",
      huggingface: "huggingface.chat_completions",
      nvidia: "nvidia.chat_completions",
      tinker: "tinker.chat_completions",
      kimi: "kimi.chat_completions",
      ai21: "ai21.chat_completions",
      arcee: "arcee.chat_completions",
      cohere: "cohere.chat_completions_compatible",
      dashscope: "dashscope.chat_completions",
      inception: "inception.chat_completions",
      poolside: "poolside.chat_completions",
      xiaomi: "xiaomi.chat_completions",
      zai: "zai.chat_completions",
      zhipu: "zhipu.chat_completions"
    };
    return surfaces[provider] || (!provider ? "openai.chat_completions" : undefined);
  }
  if (payload.metrics && typeof payload.metrics === "object" && Object.keys(usage).length > 0) {
    return "aws.bedrock.converse";
  }
  return undefined;
}

export function fromResponse(response, options = {}) {
  const resolvedOptions = {
    ...options,
    surface: options.surface || inferSurface(response, options) || "unknown"
  };
  const mode = resolvedOptions.mode || "compatibility";
  let usageLedger;
  try {
    usageLedger = extractUsageLedger(response, resolvedOptions);
  } catch (error) {
    if (mode === "strict") {
      throw error;
    }
    return unsupportedSurfaceLedger(response, resolvedOptions);
  }
  if (resolvedOptions.context && typeof resolvedOptions.context === "object") {
    usageLedger.context = { ...(usageLedger.context || {}), ...resolvedOptions.context };
    if (usageLedger.provider === "openai") {
      const contextTier = usageLedger.context.service_tier ?? usageLedger.context.serviceTier;
      if (contextTier !== undefined && contextTier !== null) {
        const normalizedTier = normalizeOpenAIServiceTier(contextTier);
        if (normalizedTier) usageLedger.context.service_tier = normalizedTier;
        delete usageLedger.context.serviceTier;
      }
    }
  }
  if (resolvedOptions.attribution && typeof resolvedOptions.attribution === "object") {
    usageLedger.attribution = normalizeAttribution(resolvedOptions.attribution);
  }
  const extractedProviderReportedCost = providerReportedCostFromRawResponse(response, usageLedger);
  const priceCards = resolvedOptions.priceCards ?? resolvedOptions.price_cards ?? [];
  return calculateCost({
    usageLedger,
    priceCards,
    discountPolicies: resolvedOptions.discountPolicies || resolvedOptions.discount_policies || [],
    mode,
    staleAfterDays: resolvedOptions.staleAfterDays,
    stale_after_days: resolvedOptions.stale_after_days,
    providerReportedCost: resolvedOptions.providerReportedCost ?? resolvedOptions.provider_reported_cost ?? extractedProviderReportedCost,
    providerReportedCostMode: resolvedOptions.providerReportedCostMode,
    provider_reported_cost_mode: resolvedOptions.provider_reported_cost_mode,
    priceSourcePriority: resolvedOptions.priceSourcePriority,
    price_source_priority: resolvedOptions.price_source_priority,
    debugTrace: resolvedOptions.debugTrace,
    debug_trace: resolvedOptions.debug_trace
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

export function fromVercelAISDKStreamFinish(result, options = {}) {
  return fromResponse(result, {
    ...options,
    adapter: "vercel_ai_sdk.stream_text"
  });
}

export function fromVercelAISDKStreamTranscribeFinish(result, options = {}) {
  return fromResponse(result, {
    ...options,
    adapter: "vercel_ai_sdk.stream_transcribe"
  });
}

export function fromLlamaIndexTokenCounter(counter, options) {
  return fromResponse(counter, {
    ...options,
    adapter: "llamaindex.token_counter"
  });
}

export function fromHaystackGeneratorResult(result, options = {}) {
  return fromResponse(result, {
    ...options,
    adapter: "haystack.generator_result"
  });
}

export function fromLiteLLMResponse(response, options = {}) {
  const hidden = response._hidden_params || response.hidden_params || {};
  const responseCost = hidden.response_cost;
  return fromResponse(response, {
    ...options,
    providerReportedCost: options.providerReportedCost ?? options.provider_reported_cost ?? responseCost,
    providerReportedCostMode: options.providerReportedCostMode ?? options.provider_reported_cost_mode ?? "compare",
    adapter: "litellm.proxy_response"
  });
}

export function fromAG2UsageSummary(summary, options = {}) {
  const { summary: usageSummary } = ag2UsageSummaryPayload(summary, options);
  const { usage } = ag2ModelUsage(usageSummary, options.model);
  const reportedCost = usage.cost || usageSummary.total_cost;
  return fromResponse(summary, {
    ...options,
    providerReportedCost: options.providerReportedCost ?? options.provider_reported_cost ?? reportedCost,
    providerReportedCostMode: options.providerReportedCostMode ?? options.provider_reported_cost_mode ?? "compare",
    adapter: "ag2.usage_summary"
  });
}

export function fromOpenAIAgentsUsage(usage, options = {}) {
  return fromResponse(usage, {
    ...options,
    adapter: "openai_agents.usage"
  });
}

function langSmithReportedCost(run) {
  const usage = run.usage_metadata && typeof run.usage_metadata === "object" ? run.usage_metadata : {};
  return run.total_cost ?? run.totalCost ?? run.cost ?? usage.total_cost ?? usage.totalCost;
}

export function fromLangSmithRun(run, options = {}) {
  const reportedCost = langSmithReportedCost(run);
  return fromResponse(run, {
    ...options,
    providerReportedCost: options.providerReportedCost ?? options.provider_reported_cost ?? reportedCost,
    providerReportedCostMode: options.providerReportedCostMode ?? options.provider_reported_cost_mode ?? "compare",
    adapter: "langsmith.run_usage"
  });
}

export function fromSemanticKernelTelemetry(telemetry, options = {}) {
  return fromResponse(telemetry, {
    ...options,
    adapter: "semantic_kernel.telemetry"
  });
}

function openRouterReportedCost(response) {
  const payload = openAICompatibleChatPayload(openRouterSDKResponsePayload(response));
  const usage = payload.usage && typeof payload.usage === "object" ? payload.usage : {};
  return usage.cost ?? usage.totalCost ?? payload.cost ?? payload.totalCost;
}

export function fromOpenRouterSDKResponse(response, options = {}) {
  const reportedCost = openRouterReportedCost(response);
  return fromResponse(response, {
    ...options,
    providerReportedCost: options.providerReportedCost ?? options.provider_reported_cost ?? reportedCost,
    providerReportedCostMode: options.providerReportedCostMode ?? options.provider_reported_cost_mode ?? "compare",
    adapter: "openrouter.sdk_response"
  });
}

export async function fromOpenRouterAgentResult(result, options = {}) {
  const response = result && typeof result.getResponse === "function"
    ? await result.getResponse()
    : (result && result.response ? result.response : result);
  return fromOpenRouterSDKResponse(response, options);
}

export function createRunCostVercelOnFinish(options = {}) {
  const ledgers = [];
  const onCostLedger = options.onCostLedger;
  const onFinish = options.onFinish;
  const costOptions = { ...options };
  delete costOptions.onCostLedger;
  delete costOptions.onFinish;

  const handler = async (result) => {
    const ledger = fromVercelAISDKStreamFinish(result, costOptions);
    ledgers.push(ledger);
    if (typeof onCostLedger === "function") {
      onCostLedger(ledger, { result });
    }
    if (typeof onFinish === "function") {
      await onFinish(result);
    }
    return ledger;
  };
  handler.ledgers = ledgers;
  Object.defineProperty(handler, "latest", {
    get() {
      return ledgers.length > 0 ? ledgers[ledgers.length - 1] : null;
    }
  });
  return handler;
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

const ATTRIBUTION_KEYS = ["run_id", "session_id", "workflow", "tenant_id", "feature"];

function attributionString(value) {
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return Number.isFinite(value) ? canonicalDecimal(value) : undefined;
  if (typeof value === "bigint") return value.toString();
  return undefined;
}

export function normalizeAttribution(value = {}) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  const result = {};
  for (const key of ATTRIBUTION_KEYS) {
    const normalized = attributionString(value[key]);
    if (normalized !== undefined) result[key] = normalized;
  }
  if (value.tags && typeof value.tags === "object" && !Array.isArray(value.tags)) {
    const tags = Object.fromEntries(
      Object.entries(value.tags)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, child]) => [String(key), attributionString(child)])
        .filter(([, child]) => child !== undefined)
    );
    if (Object.keys(tags).length > 0) result.tags = tags;
  }
  return result;
}

function batchError(value, fallback) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const result = { ...value };
    result.message = String(result.message ?? result.detail ?? result.status ?? fallback);
    return result;
  }
  return { message: value === undefined || value === null || value === "" ? fallback : String(value) };
}

function batchSurfaceFromEndpoint(endpoint, fallback) {
  if (fallback) return fallback;
  const text = String(endpoint || "").toLowerCase();
  if (text.includes("responses")) return "openai.responses";
  if (text.includes("chat/completions")) return "openai.chat_completions";
  if (text.includes("embeddings")) return "openai.embeddings";
  if (text.includes("images")) return "openai.images";
  if (text.includes("audio/transcriptions")) return "openai.audio_transcriptions";
  return undefined;
}

function batchItemId(item, index) {
  for (const key of ["custom_id", "customId", "recordId", "record_id", "key", "id"]) {
    if (item[key] !== undefined && item[key] !== null && item[key] !== "") return String(item[key]);
  }
  const labels = item.request && typeof item.request === "object" && item.request.labels && typeof item.request.labels === "object"
    ? item.request.labels : {};
  for (const key of ["id", "key", "custom_id"]) {
    if (labels[key] !== undefined && labels[key] !== null && labels[key] !== "") return String(labels[key]);
  }
  const response = item.response && typeof item.response === "object" ? item.response : {};
  for (const key of ["responseId", "response_id", "id"]) {
    if (response[key] !== undefined && response[key] !== null && response[key] !== "") return String(response[key]);
  }
  return String(index);
}

function unwrapBatchItem(item, options) {
  const provider = String(options.provider || "").toLowerCase().replaceAll("_", "-");
  if (["openai", "kimi", "moonshot", "moonshot-ai", "dashscope", "alibaba"].includes(provider)) {
    const outer = item.response && typeof item.response === "object" ? item.response : {};
    const rawStatus = outer.status_code ?? outer.statusCode;
    const httpStatus = rawStatus === undefined || rawStatus === null ? undefined : Number(rawStatus);
    if (item.error || (Number.isFinite(httpStatus) && (httpStatus < 200 || httpStatus >= 300))) {
      return { status: "errored", error: batchError(item.error || outer.body, "OpenAI batch item failed."), httpStatus };
    }
    if (!outer.body || typeof outer.body !== "object") {
      return { status: "pending", error: batchError(null, "OpenAI batch item has no response body yet."), httpStatus };
    }
    return {
      status: "succeeded",
      response: outer.body,
      httpStatus,
      surface: provider === "openai"
        ? batchSurfaceFromEndpoint(options.endpoint || item.url, options.surface)
        : (options.surface || (["dashscope", "alibaba"].includes(provider) ? "dashscope.chat_completions" : "kimi.chat_completions"))
    };
  }
  if (provider === "anthropic") {
    const result = item.result && typeof item.result === "object" ? item.result : {};
    const type = String(result.type || "pending").toLowerCase();
    if (type === "succeeded" && result.message && typeof result.message === "object") {
      return { status: "succeeded", response: result.message, surface: "anthropic.messages" };
    }
    const status = ["errored", "canceled", "expired"].includes(type) ? type : "pending";
    return { status, error: batchError(result.error || item.error, `Anthropic batch item is ${status}.`) };
  }
  if (["google", "gemini", "google-gemini"].includes(provider)) {
    if (item.response && typeof item.response === "object") {
      return { status: "succeeded", response: item.response, surface: "google.gemini.generate_content" };
    }
    if ((item.usageMetadata && typeof item.usageMetadata === "object") || (item.usage_metadata && typeof item.usage_metadata === "object")) {
      return { status: "succeeded", response: item, surface: "google.gemini.generate_content" };
    }
    if (item.error || item.status) {
      return { status: "errored", error: batchError(item.error || item.status, "Gemini batch item failed.") };
    }
    return { status: "pending", error: batchError(null, "Gemini batch item has no response yet.") };
  }
  if (["vertex", "google-vertex", "vertex-ai"].includes(provider)) {
    if (item.response && typeof item.response === "object" && Object.keys(item.response).length > 0) {
      return {
        status: "succeeded",
        response: item.response,
        surface: "vertex.gemini.generate_content",
        metadata: Object.fromEntries(["processed_time", "processedTime"].filter((key) => item[key] !== undefined).map((key) => [key, item[key]]))
      };
    }
    if (item.status) return { status: "errored", error: batchError(item.status, "Vertex batch item failed.") };
    return { status: "pending", error: batchError(null, "Vertex batch item has no response yet.") };
  }
  if (["bedrock", "aws-bedrock"].includes(provider)) {
    if (item.error) return { status: "errored", error: batchError(item.error, "Bedrock batch item failed.") };
    const response = item.modelOutput ?? item.model_output;
    if (response && typeof response === "object") {
      return { status: "succeeded", response, surface: options.surface || "aws.bedrock.invoke_model" };
    }
    return { status: "pending", error: batchError(null, "Bedrock batch item has no modelOutput yet.") };
  }
  throw new Error(`unsupported batch provider: ${options.provider}`);
}

export function fromBatchResults(items, options = {}) {
  if (!options.provider) throw new Error("provider is required for batch results");
  const normalizedProvider = String(options.provider).toLowerCase().replaceAll("_", "-");
  const supportedProviders = new Set([
    "openai", "kimi", "moonshot", "moonshot-ai", "dashscope", "alibaba", "anthropic",
    "google", "gemini", "google-gemini", "vertex", "google-vertex", "vertex-ai", "bedrock", "aws-bedrock"
  ]);
  if (!supportedProviders.has(normalizedProvider)) throw new Error(`unsupported batch provider: ${options.provider}`);
  const attribution = normalizeAttribution(options.attribution);
  const cards = compilePriceCatalog(options.priceCards ?? options.price_cards ?? []);
  const outputItems = [];
  const ledgers = [];
  [...items].forEach((rawItem, index) => {
    const item = rawItem && typeof rawItem === "object" ? rawItem : {};
    const id = batchItemId(item, index);
    const unwrapped = unwrapBatchItem(item, options);
    const output = { id, status: unwrapped.status };
    if (unwrapped.httpStatus !== undefined) output.http_status = unwrapped.httpStatus;
    if (unwrapped.metadata && Object.keys(unwrapped.metadata).length > 0) output.metadata = unwrapped.metadata;
    output.metadata = {
      ...(output.metadata || {}),
      service_tier: "batch",
      batch_item_id: id
    };
    if (options.batchId ?? options.batch_id) output.metadata.batch_id = options.batchId ?? options.batch_id;
    if (options.endpoint) output.metadata.endpoint = options.endpoint;
    if (Object.keys(attribution).length > 0) output.attribution = { ...attribution };
    if (unwrapped.status === "succeeded") {
      if (!unwrapped.surface) throw new Error(`surface or endpoint is required for ${options.provider} batch item ${id}`);
      const context = {
        ...(options.context || {}),
        service_tier: "batch",
        batch_item_id: id
      };
      if (options.batchId ?? options.batch_id) context.batch_id = options.batchId ?? options.batch_id;
      const ledger = fromResponse(unwrapped.response, {
        ...options,
        provider: ["google", "gemini", "google-gemini"].includes(String(options.provider).toLowerCase()) ? "google"
          : ["vertex", "google-vertex", "vertex-ai"].includes(String(options.provider).toLowerCase()) ? "vertex"
          : ["bedrock", "aws-bedrock"].includes(String(options.provider).toLowerCase()) ? "bedrock"
          : ["kimi", "moonshot", "moonshot-ai"].includes(String(options.provider).toLowerCase()) ? "kimi"
          : ["dashscope", "alibaba"].includes(String(options.provider).toLowerCase()) ? "dashscope"
          : options.provider,
        surface: unwrapped.surface,
        context,
        attribution,
        priceCards: cards
      });
      output.ledger = ledger;
      if (normalizedProvider === "anthropic") {
        const refusal = ledger.metadata && ledger.metadata.anthropic_refusal;
        if (refusal && typeof refusal === "object" && refusal.detected === true) {
          output.metadata.refusal = true;
          output.metadata.requires_retry = Boolean(refusal.requires_retry);
          if (refusal.recommended_model) output.metadata.recommended_model = refusal.recommended_model;
        }
      }
      ledgers.push(ledger);
    } else {
      output.error = unwrapped.error || batchError(null, `Batch item is ${unwrapped.status}.`);
    }
    outputItems.push(output);
  });
  const aggregate = aggregateCostLedgers({
    costLedgers: ledgers,
    provider: options.provider,
    surface: `${options.provider}.batch`,
    model: options.model || "multiple",
    mode: options.mode || "compatibility",
    attribution
  });
  const succeeded = outputItems.filter((item) => item.status === "succeeded").length;
  const pending = outputItems.filter((item) => item.status === "pending").length;
  const failed = outputItems.length - succeeded - pending;
  const warnings = [];
  if (failed) warnings.push({
    code: "batch_items_failed",
    message: `${failed} batch item(s) did not succeed and remain visible in items.`,
    metadata: { failed, total: outputItems.length }
  });
  if (pending) warnings.push({
    code: "batch_items_pending",
    message: `${pending} batch item(s) have no terminal result yet.`,
    metadata: { pending, total: outputItems.length }
  });
  const result = {
    schema_version: "0.1",
    provider: options.provider,
    surface: `${options.provider}.batch`,
    currency: "USD",
    items: outputItems,
    summary: { total: outputItems.length, succeeded, failed, pending, total_cost: aggregate.total },
    aggregate,
    warnings
  };
  const batchId = options.batchId ?? options.batch_id;
  if (batchId) result.batch_id = String(batchId);
  if (Object.keys(attribution).length > 0) result.attribution = attribution;
  return result;
}

function staticMatchAliases(match) {
  if (!match || typeof match !== "object" || Array.isArray(match)) return { aliases: [], unsupported: false };
  if (typeof match.equals === "string") return { aliases: [match.equals], unsupported: false };
  if (Array.isArray(match.or)) {
    const children = match.or.map(staticMatchAliases);
    return {
      aliases: [...new Set(children.flatMap((child) => child.aliases))].sort(),
      unsupported: children.some((child) => child.unsupported)
    };
  }
  return { aliases: [], unsupported: Object.keys(match).length > 0 };
}

function tierValues(value) {
  if (!value || typeof value !== "object" || Array.isArray(value) || !hasOwn(value, "base")) {
    return value === undefined || value === null ? [] : [{ amount: value }];
  }
  const tiers = (value.tiers || []).filter((tier) => tier && typeof tier === "object" && tier.start !== undefined)
    .sort((left, right) => Number(left.start) - Number(right.start));
  const result = [{ amount: value.base, maximum: tiers.length ? subtractDecimal(tiers[0].start, "1") : undefined }];
  tiers.forEach((tier, index) => result.push({
    amount: tier.price,
    minimum: tier.start,
    maximum: index + 1 < tiers.length ? subtractDecimal(tiers[index + 1].start, "1") : undefined
  }));
  return result.filter((entry) => entry.amount !== undefined && entry.amount !== null);
}

const GENAI_PRICE_COMPONENTS = {
  input_mtok: ["input_uncached_tokens", "token", "1000000"],
  cache_write_mtok: ["input_cache_write_tokens", "token", "1000000"],
  cache_read_mtok: ["input_cache_read_tokens", "token", "1000000"],
  output_mtok: ["output_text_tokens", "token", "1000000"],
  input_audio_mtok: ["input_audio_tokens", "token", "1000000"],
  cache_audio_read_mtok: ["input_cache_read_tokens", "token", "1000000"],
  output_audio_mtok: ["output_audio_tokens", "token", "1000000"],
  requests_kcount: ["request_units", "request", "1000"]
};

function genAIPriceComponents(prices) {
  const components = [];
  const warnings = [];
  for (const [key, value] of Object.entries(prices || {})) {
    const mapping = GENAI_PRICE_COMPONENTS[key];
    if (!mapping) {
      warnings.push(`unsupported price field retained in metadata: ${key}`);
      continue;
    }
    const [usageComponent, unit, per] = mapping;
    for (const tier of tierValues(value)) {
      const component = {
        usage_component: usageComponent,
        unit,
        price: { amount: normalizeDecimalString(tier.amount), currency: "USD", per }
      };
      const conditions = {};
      if (tier.minimum !== undefined) conditions.min_total_input_tokens = normalizeDecimalString(tier.minimum);
      if (tier.maximum !== undefined) conditions.max_total_input_tokens = normalizeDecimalString(tier.maximum);
      if (Object.keys(conditions).length > 0) component.conditions = conditions;
      components.push(component);
    }
  }
  return { components, warnings };
}

const GENAI_CONSTRAINT_ALIASES = Object.freeze({
  start_date: ["start_date", "startDate"],
  start_time: ["start_time", "startTime"],
  end_time: ["end_time", "endTime"],
  timezone: ["timezone", "timeZone"],
  days_of_week: ["days_of_week", "daysOfWeek"]
});

function genAIConstraintFields(constraint) {
  if (!constraint || typeof constraint !== "object" || Array.isArray(constraint)) return null;
  const allowed = new Set(Object.values(GENAI_CONSTRAINT_ALIASES).flat());
  if (Object.keys(constraint).some((key) => !allowed.has(key))) return null;
  const fields = {};
  for (const [canonical, aliases] of Object.entries(GENAI_CONSTRAINT_ALIASES)) {
    const present = aliases.filter((key) => hasOwn(constraint, key));
    if (present.length > 1) return null;
    if (present.length === 1) fields[canonical] = constraint[present[0]];
  }
  return fields;
}

function genAIScheduleConstraint(constraint) {
  const fields = genAIConstraintFields(constraint);
  if (!fields) return { supported: false };
  if (hasOwn(fields, "start_date") && !dateOnlyValue(fields.start_date)) {
    return { supported: false };
  }
  const hasStartTime = hasOwn(fields, "start_time");
  const hasEndTime = hasOwn(fields, "end_time");
  const hasTime = hasStartTime || hasEndTime;
  const hasTimezone = hasOwn(fields, "timezone");
  const hasDays = hasOwn(fields, "days_of_week");
  if (!hasTime && (hasTimezone || hasDays)) return { supported: false };
  if (!hasTime) return { supported: true, hasTime: false, fields, startDate: fields.start_date };
  if (!hasStartTime || !hasEndTime || typeof fields.start_time !== "string" || typeof fields.end_time !== "string") {
    return { supported: false };
  }

  const timezone = hasTimezone ? fields.timezone : "UTC";
  const timezoneResult = billingScheduleTimezone({ timezone });
  if (timezoneResult.unsupported_timezone) return { supported: false };
  if ((fields.start_time.endsWith("Z") || fields.end_time.endsWith("Z")) && timezoneResult.timezone !== "UTC") {
    return { supported: false };
  }
  const start = fields.start_time.replace(/Z$/, "");
  const end = fields.end_time.replace(/Z$/, "");
  if (timeSeconds(start) === null || timeSeconds(end) === null) {
    return { supported: false };
  }
  const daysResult = hasDays
    ? billingWindowDays({ days_of_week: fields.days_of_week })
    : { days: null };
  if (daysResult.unsupported_schedule) return { supported: false };
  return {
    supported: true,
    hasTime: true,
    timezone: timezoneResult.timezone,
    start,
    end,
    days: daysResult.days,
    fields,
    startDate: fields.start_date
  };
}

function previousDay(value) {
  const parsed = new Date(`${value}T00:00:00Z`);
  parsed.setUTCDate(parsed.getUTCDate() - 1);
  return parsed.toISOString().slice(0, 10);
}

export function priceCardsFromGenAIPrices(data, options = {}) {
  const providers = Array.isArray(data) ? data : (data && Array.isArray(data.providers) ? data.providers : []);
  const cards = [];
  for (const rawProvider of providers) {
    if (!rawProvider || typeof rawProvider !== "object") continue;
    const provider = String(rawProvider.id || "unknown");
    const source = { name: "genai-prices" };
    if (Array.isArray(rawProvider.pricing_urls) && rawProvider.pricing_urls.length) source.url = String(rawProvider.pricing_urls[0]);
    const retrievedAt = options.retrievedAt ?? options.retrieved_at;
    const version = options.version ?? options.sourceVersion ?? options.source_version;
    if (retrievedAt) source.retrieved_at = String(retrievedAt);
    if (version) source.version = String(version);
    for (const rawModel of rawProvider.models || []) {
      if (!rawModel || typeof rawModel !== "object" || !rawModel.id) continue;
      const model = String(rawModel.id);
      const match = staticMatchAliases(rawModel.match);
      const aliases = match.aliases.filter((alias) => alias !== model);
      const conditional = Array.isArray(rawModel.prices) ? rawModel.prices : [{ prices: rawModel.prices || {} }];
      const constraintDetails = new Map();
      conditional.forEach((entry, index) => {
        if (!entry || typeof entry !== "object" || Array.isArray(entry)) return;
        const rawConstraint = entry.constraint ?? {};
        if (typeof rawConstraint !== "object" || Array.isArray(rawConstraint)) return;
        const scheduleConstraint = genAIScheduleConstraint(rawConstraint);
        if (scheduleConstraint.supported) constraintDetails.set(index, scheduleConstraint);
      });
      const datedStarts = [...constraintDetails.values()]
        .map((detail) => detail.startDate)
        .filter(Boolean)
        .map(String)
        .sort();
      const scheduledEntries = [...constraintDetails.entries()]
        .filter(([, detail]) => detail.hasTime)
        .map(([index, detail]) => ({ index, ...detail }));
      const scheduledTimezones = new Set(scheduledEntries.map((entry) => entry.timezone));
      const schedule = scheduledEntries.length > 0 && scheduledTimezones.size === 1 ? {
        timezone: scheduledEntries[0].timezone,
        default_period: "default",
        boundary_policy: "start_inclusive_end_exclusive",
        windows: scheduledEntries.map((entry, periodIndex) => ({
          period: `scheduled-${periodIndex + 1}`,
          start: entry.start,
          end: entry.end,
          ...(entry.days ? { days_of_week: [...entry.days] } : {})
        }))
      } : undefined;
      const scheduledEntryIndexes = new Map(
        scheduledEntries.map((entry, periodIndex) => [entry.index, { ...entry, periodIndex }])
      );
      const usedCardIds = new Set();
      conditional.forEach((entry, index) => {
        if (!entry || typeof entry !== "object" || !entry.prices || typeof entry.prices !== "object") return;
        const rawConstraint = entry.constraint ?? {};
        const scheduleConstraint = constraintDetails.get(index);
        if (!scheduleConstraint) return;
        const constraint = scheduleConstraint.fields;
        const scheduledEntry = scheduledEntryIndexes.get(index);
        if (scheduleConstraint.hasTime && (!schedule || !scheduledEntry)) return;
        const converted = genAIPriceComponents(entry.prices);
        if (!converted.components.length) return;
        const adapterWarnings = [...converted.warnings];
        if (match.unsupported) adapterWarnings.push("non-enumerable model match clause retained in metadata");
        const card = {
          schema_version: "0.1",
          id: `${provider}:${model}:genai-prices:${index}`,
          provider,
          model,
          aliases,
          components: converted.components,
          source,
          metadata: {
            genai_prices: {
              provider_name: rawProvider.name ?? null,
              provider_match: rawProvider.provider_match ?? null,
              model_match: rawModel.match ?? null,
              api_pattern: rawProvider.api_pattern ?? null,
              context_window: rawModel.context_window ?? null,
              constraint: rawConstraint
            }
          }
        };
        let suffix = "current";
        if (constraint.start_date) {
          const start = String(constraint.start_date);
          suffix = start;
          card.effective = { from: start };
          const later = datedStarts.filter((candidate) => candidate > start);
          if (later.length) card.effective.to = previousDay(later[0]);
        } else if (datedStarts.length && !Object.keys(constraint).length) {
          suffix = "historical";
          card.effective = { to: previousDay(datedStarts[0]) };
        }
        if (scheduleConstraint.hasTime) {
          suffix = `scheduled-${scheduledEntry.periodIndex + 1}`;
          card.pricing_period = suffix;
          card.billing_schedule = schedule;
        } else if (schedule) {
          suffix = suffix === "current" ? "default" : `${suffix}-default`;
          card.pricing_period = "default";
          card.billing_schedule = schedule;
        }
        if (adapterWarnings.length) card.metadata.adapter_warnings = [...new Set(adapterWarnings)].sort();
        const baseId = `${provider}:${model}:genai-prices:${suffix}`;
        card.id = usedCardIds.has(baseId) ? `${baseId}:${index}` : baseId;
        usedCardIds.add(card.id);
        cards.push(card);
      });
    }
  }
  return cards;
}

const OTEL_PROVIDER_MAP = {
  openai: "openai",
  anthropic: "anthropic",
  "aws.bedrock": "bedrock",
  "azure.ai.openai": "azure",
  "gcp.gen_ai": "google",
  "gcp.vertex_ai": "vertex",
  x_ai: "xai"
};

function otelAttributes(span) {
  if (span && span.attributes && typeof span.attributes === "object") return { ...span.attributes };
  return Object.fromEntries(Object.entries(span || {}).filter(([key]) => key.includes(".")));
}

function otelSurface(provider, operation) {
  if (operation === "generate_content") return provider === "vertex" ? "vertex.gemini.generate_content" : "google.gemini.generate_content";
  if (provider === "anthropic") return "anthropic.messages";
  if (provider === "bedrock") return "aws.bedrock.converse";
  if (operation === "embeddings") return "openai.embeddings";
  return provider === "openai" ? "openai.chat_completions" : `${provider}.chat_completions`;
}

export function usageLedgerFromOTelGenAISpan(span, options = {}) {
  const attributes = otelAttributes(span);
  const providerAttribute = String(attributes["gen_ai.provider.name"] || "");
  const provider = options.provider || OTEL_PROVIDER_MAP[providerAttribute] || providerAttribute || "unknown";
  const operation = String(attributes["gen_ai.operation.name"] || "chat");
  const requestedModel = String(options.model || attributes["gen_ai.request.model"] || attributes["gen_ai.response.model"] || "unknown");
  const returnedModel = String(attributes["gen_ai.response.model"] || requestedModel);
  const inputTotal = attributes["gen_ai.usage.input_tokens"] || 0;
  const outputTotal = attributes["gen_ai.usage.output_tokens"] || 0;
  const cacheWrite = attributes["gen_ai.usage.cache_creation.input_tokens"] || 0;
  const cacheRead = attributes["gen_ai.usage.cache_read.input_tokens"] || 0;
  const reasoning = attributes["gen_ai.usage.reasoning.output_tokens"] || 0;
  const componentValues = [
    ["input_uncached_tokens", subtractDecimal(subtractDecimal(inputTotal, cacheWrite), cacheRead), "$.attributes.gen_ai.usage.input_tokens"],
    ["input_cache_read_tokens", cacheRead, "$.attributes.gen_ai.usage.cache_read.input_tokens"],
    ["input_cache_write_tokens", cacheWrite, "$.attributes.gen_ai.usage.cache_creation.input_tokens"],
    ["output_text_tokens", subtractDecimal(outputTotal, reasoning), "$.attributes.gen_ai.usage.output_tokens"],
    ["output_reasoning_tokens", reasoning, "$.attributes.gen_ai.usage.reasoning.output_tokens"]
  ];
  const components = componentValues.map(([name, rawQuantity, sourcePath]) => {
    const quantity = parseDecimal(rawQuantity).value < 0n ? "0" : normalizeDecimalString(rawQuantity);
    return positiveComponent(name, quantity, "token", sourcePath);
  }).filter(Boolean);
  const context = {};
  const serviceTier = attributes["gen_ai.request.service_tier"] || attributes["gen_ai.response.service_tier"] ||
    attributes["openai.response.service_tier"] || attributes["openai.request.service_tier"];
  if (serviceTier) {
    const normalizedTier = provider === "openai" ? normalizeOpenAIServiceTier(serviceTier) : String(serviceTier);
    if (normalizedTier) context.service_tier = normalizedTier;
  }
  const requestId = attributes["gen_ai.response.id"] || attributes["openai.response.id"];
  if (requestId) context.request_id = String(requestId);
  const traceId = span && (span.trace_id ?? span.traceId);
  if (traceId) context.trace_id = String(traceId);
  const known = new Set([
    "gen_ai.provider.name", "gen_ai.operation.name", "gen_ai.request.model", "gen_ai.response.model",
    "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens", "gen_ai.usage.cache_creation.input_tokens",
    "gen_ai.usage.cache_read.input_tokens", "gen_ai.usage.reasoning.output_tokens"
  ]);
  const ledger = {
    schema_version: "0.1",
    provider,
    surface: options.surface || otelSurface(provider, operation),
    model: { requested: requestedModel, returned: returnedModel, billed: requestedModel, alias_resolution: "none" },
    components,
    raw_usage: Object.fromEntries(Object.entries(attributes).filter(([key]) => key.startsWith("gen_ai.usage."))),
    metadata: {
      otel_genai: {
        operation,
        provider_attribute: attributes["gen_ai.provider.name"],
        unknown_attributes: Object.fromEntries(Object.entries(attributes).filter(([key]) => key.startsWith("gen_ai.") && !known.has(key)))
      }
    }
  };
  if (Object.keys(context).length) ledger.context = context;
  const attribution = normalizeAttribution(options.attribution);
  if (Object.keys(attribution).length) ledger.attribution = attribution;
  return ledger;
}

export function fromOTelGenAISpan(span, options = {}) {
  const usageLedger = usageLedgerFromOTelGenAISpan(span, options);
  const priceCards = compilePriceCatalog(options.priceCards ?? options.price_cards ?? []);
  return calculateCost({
    usageLedger,
    priceCards,
    discountPolicies: options.discountPolicies ?? options.discount_policies ?? [],
    mode: options.mode || "compatibility",
    staleAfterDays: options.staleAfterDays,
    stale_after_days: options.stale_after_days,
    debugTrace: options.debugTrace,
    debug_trace: options.debug_trace
  });
}

export function otelCostAttributes(costLedger, options = {}) {
  const prefix = options.prefix || "runcost";
  const warnings = Array.isArray(costLedger.warnings) ? costLedger.warnings : [];
  return {
    [`${prefix}.cost.total`]: String(costLedger.total || "0"),
    [`${prefix}.cost.currency`]: String(costLedger.currency || "USD"),
    [`${prefix}.cost.component_count`]: (costLedger.components || []).length,
    [`${prefix}.cost.warning_count`]: warnings.length,
    [`${prefix}.cost.warning_codes`]: warnings.map((warning) => String(warning.code)),
    [`${prefix}.cost.price_card_ids`]: [...new Set((costLedger.components || []).map((component) => component.price_card_id).filter(Boolean).map(String))].sort()
  };
}

export function estimateCost(options = {}) {
  const rawComponents = Array.isArray(options.components)
    ? options.components
    : Object.entries(options.components || {}).map(([name, quantity]) => ({ name, quantity }));
  const usageLedger = {
    schema_version: "0.1",
    provider: options.provider,
    surface: options.surface,
    model: { requested: options.model, returned: options.model, billed: options.model, alias_resolution: "none" },
    components: rawComponents.map((component) => ({ ...component, quantity: normalizeDecimalString(component.quantity || 0), unit: component.unit || "token" })),
    metadata: { estimate: true }
  };
  if (options.context) usageLedger.context = { ...options.context };
  const attribution = normalizeAttribution(options.attribution);
  if (Object.keys(attribution).length) usageLedger.attribution = attribution;
  const priceCards = compilePriceCatalog(options.priceCards ?? options.price_cards ?? []);
  return calculateCost({
    usageLedger,
    priceCards,
    discountPolicies: options.discountPolicies ?? options.discount_policies ?? [],
    mode: options.mode || "compatibility",
    staleAfterDays: options.staleAfterDays,
    stale_after_days: options.stale_after_days,
    debugTrace: options.debugTrace,
    debug_trace: options.debug_trace
  });
}

export function evaluateBudget(ledgerOrTotal, options = {}) {
  const ledger = ledgerOrTotal && typeof ledgerOrTotal === "object" ? ledgerOrTotal : null;
  const total = ledger ? ledger.total || "0" : ledgerOrTotal;
  const budget = normalizeDecimalString(options.budget);
  const threshold = normalizeDecimalString(options.warningThreshold ?? options.warning_threshold ?? "0.8");
  if (parseDecimal(budget).value < 0n) throw new Error("budget must be non-negative");
  if (compareDecimal(threshold, "0") < 0 || compareDecimal(threshold, "1") > 0) throw new Error("warning_threshold must be between 0 and 1");
  const warningAmount = multiplyDivideDecimal(budget, threshold, "1");
  const status = compareDecimal(total, budget) > 0
    ? "exceeded"
    : compareDecimal(budget, "0") > 0 && compareDecimal(total, warningAmount) >= 0
      ? "warning"
      : "within_budget";
  const result = {
    schema_version: "0.1",
    status,
    estimated_cost: normalizeDecimalString(total),
    budget,
    remaining: subtractDecimal(budget, total),
    warning_threshold: threshold,
    currency: ledger ? ledger.currency || "USD" : "USD"
  };
  if (ledger) result.ledger = ledger;
  return result;
}

export function reconcileCost(costLedgerOrTotal, reportedTotal, options = {}) {
  const ledger = costLedgerOrTotal && typeof costLedgerOrTotal === "object" ? costLedgerOrTotal : null;
  const calculated = canonicalDecimal(ledger ? ledger.total || "0" : costLedgerOrTotal);
  const reported = canonicalDecimal(reportedTotal);
  const tolerance = canonicalDecimal(options.tolerance || "0");
  if (parseDecimal(tolerance).value < 0n) throw new Error("tolerance must be non-negative");
  const residual = subtractDecimal(reported, calculated);
  const absolute = residual.startsWith("-") ? residual.slice(1) : residual;
  const status = compareDecimal(absolute, "0") === 0 ? "matched" : compareDecimal(absolute, tolerance) <= 0 ? "within_tolerance" : "mismatch";
  return {
    schema_version: "0.1",
    status,
    calculated_total: calculated,
    reported_total: reported,
    signed_residual: residual,
    absolute_residual: absolute,
    tolerance,
    currency: ledger ? ledger.currency || options.currency || "USD" : options.currency || "USD"
  };
}

const EXTERNAL_PRICE_MEMORY_CACHE = new Map();
const EXTERNAL_PRICE_DISK_CACHE = new Map();
const EXTERNAL_PRICE_COMPILED_CATALOGS = new WeakMap();
const INCOMPLETE_PRICE_WARNING_CODES = new Set([
  "unknown_provider", "unknown_model", "price_not_found", "component_unpriced",
  "tool_component_unpriced", "source_capability_unsupported", "service_tier_unsupported",
  "long_context_rule_missing", "historical_price_missing", "pricing_period_required",
  "pricing_period_unsupported", "billing_schedule_unsupported"
]);

function nodeRuntimeAvailable() {
  return typeof RUNCOST_BROWSER_RUNTIME === "undefined" && typeof process !== "undefined" && Boolean(process.versions && process.versions.node);
}

function clonePriceValue(value) {
  return typeof structuredClone === "function" ? structuredClone(value) : JSON.parse(JSON.stringify(value));
}

export function defaultPriceCacheDir() {
  if (!nodeRuntimeAvailable()) return "memory://runcost/prices";
  if (process.env.RUNCOST_PRICE_CACHE_DIR) return path.resolve(process.env.RUNCOST_PRICE_CACHE_DIR);
  const home = process.env.HOME || process.env.USERPROFILE || ".";
  if (process.platform === "darwin") return path.join(home, "Library", "Caches", "runcost", "prices");
  if (process.platform === "win32") {
    return path.join(process.env.LOCALAPPDATA || path.join(home, "AppData", "Local"), "runcost", "prices");
  }
  return path.join(process.env.XDG_CACHE_HOME || path.join(home, ".cache"), "runcost", "prices");
}

function resolverNow(value) {
  const result = value instanceof Date ? new Date(value.getTime()) : value ? new Date(value) : new Date();
  if (Number.isNaN(result.getTime())) throw new TypeError("now must be a valid ISO timestamp, Date, or undefined");
  return result;
}

function resolverTimestamp(value) {
  return value.toISOString().replace(/\.\d{3}Z$/, "Z");
}

function parseResolverTimestamp(value) {
  if (!value) return null;
  const result = new Date(value);
  return Number.isNaN(result.getTime()) ? null : result;
}

function resolverSafeURL(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || (url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname));
  } catch {
    return false;
  }
}

async function resolverChecksum(value) {
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
  return `sha256:${await sha256Bytes(bytes)}`;
}

async function resolverCacheKey(source, url) {
  const safeSource = String(source).replace(/[^A-Za-z0-9.-]/g, "-");
  const urlHash = await sha256Bytes(new TextEncoder().encode(url));
  return `${safeSource}-${urlHash.slice(0, 12)}.json`;
}

async function readResolverCache(cacheDir, source, url) {
  const cacheKey = await resolverCacheKey(source, url);
  let data;
  if (!nodeRuntimeAvailable() || String(cacheDir).startsWith("memory://")) {
    data = EXTERNAL_PRICE_MEMORY_CACHE.get(`${cacheDir}/${cacheKey}`);
  } else {
    const filePath = path.join(cacheDir, cacheKey);
    if (!fs.existsSync(filePath)) return { cacheKey, data: null };
    const stat = fs.statSync(filePath);
    const signature = `${stat.ino}:${stat.size}:${stat.mtimeMs}`;
    const memoized = EXTERNAL_PRICE_DISK_CACHE.get(filePath);
    if (memoized?.signature === signature) return { cacheKey, data: memoized.data };
    try {
      data = JSON.parse(fs.readFileSync(filePath, "utf8"));
    } catch {
      return { cacheKey, data: null };
    }
    EXTERNAL_PRICE_DISK_CACHE.set(filePath, { signature, data });
  }
  if (!data || data.schema_version !== "0.1" || !data.source || !Array.isArray(data.price_cards)) return { cacheKey, data: null };
  if (data.source.name !== source || data.source.url !== url) return { cacheKey, data: null };
  if (data.cards_checksum && await resolverChecksum(stableStringify(data.price_cards)) !== data.cards_checksum) {
    return { cacheKey, data: null };
  }
  return { cacheKey, data };
}

function atomicWriteResolverCache(cacheDir, cacheKey, data) {
  const cloned = clonePriceValue(data);
  if (!nodeRuntimeAvailable() || String(cacheDir).startsWith("memory://")) {
    EXTERNAL_PRICE_MEMORY_CACHE.set(`${cacheDir}/${cacheKey}`, cloned);
    return;
  }
  fs.mkdirSync(cacheDir, { recursive: true });
  const destination = path.join(cacheDir, cacheKey);
  const temporary = path.join(cacheDir, `.${cacheKey}.${process.pid}.${Date.now()}.tmp`);
  try {
    fs.writeFileSync(temporary, `${JSON.stringify(cloned, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
    fs.renameSync(temporary, destination);
    const stat = fs.statSync(destination);
    EXTERNAL_PRICE_DISK_CACHE.set(destination, { signature: `${stat.ino}:${stat.size}:${stat.mtimeMs}`, data: cloned });
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}

function compiledExternalPriceCatalog(priceCards) {
  if (priceCards?.__runcostCompiledCatalog === true) return priceCards;
  if (!Array.isArray(priceCards)) return compilePriceCatalog(priceCards || []);
  const cached = EXTERNAL_PRICE_COMPILED_CATALOGS.get(priceCards);
  if (cached) return cached;
  const compiled = compilePriceCatalog(priceCards);
  EXTERNAL_PRICE_COMPILED_CATALOGS.set(priceCards, compiled);
  return compiled;
}

function resolverCacheAge(cache, now) {
  const checked = parseResolverTimestamp(cache?.source?.validated_at || cache?.source?.retrieved_at);
  return checked ? Math.max(0, (now.getTime() - checked.getTime()) / 1000) : null;
}

function resolverSourceWarning(code, source, status) {
  return {
    code,
    message: code === "price_source_refresh_failed"
      ? `Could not refresh external price source ${source}; using its last-known-good cache.`
      : `External price source ${source} is unavailable and has no usable cache.`,
    metadata: { source, status }
  };
}

async function fetchResolverSource(url, options) {
  if (!resolverSafeURL(url)) throw new Error("price source URL must use HTTPS (loopback HTTP is allowed for tests)");
  const controller = typeof AbortController === "function" ? new AbortController() : null;
  const timeoutId = controller ? setTimeout(() => controller.abort(), options.timeoutMs) : null;
  try {
    const fetcher = options.fetcher || globalThis.fetch;
    if (typeof fetcher !== "function") throw new Error("Fetch API is unavailable in this runtime");
    const response = await fetcher(url, {
      headers: { Accept: "application/json", ...options.headers },
      redirect: "follow",
      signal: controller?.signal
    });
    const status = Number(response.status ?? 200);
    const headers = {};
    if (response.headers && typeof response.headers.forEach === "function") {
      response.headers.forEach((value, key) => { headers[String(key).toLowerCase()] = String(value); });
    } else if (response.headers && typeof response.headers === "object") {
      Object.entries(response.headers).forEach(([key, value]) => { headers[String(key).toLowerCase()] = String(value); });
    }
    const finalURL = String(response.url || url);
    if (!resolverSafeURL(finalURL)) throw new Error("price source redirected to an unsupported URL");
    if (status === 304) return { status, headers, body: new Uint8Array(), url: finalURL };
    let body;
    if (typeof response.arrayBuffer === "function") body = new Uint8Array(await response.arrayBuffer());
    else if (response.body instanceof Uint8Array) body = response.body;
    else if (typeof response.body === "string") body = new TextEncoder().encode(response.body);
    else if (typeof response.text === "function") body = new TextEncoder().encode(await response.text());
    else throw new Error("price source response has no readable body");
    if (body.byteLength > options.maxBytes) throw new Error(`price source exceeds the ${options.maxBytes}-byte safety limit`);
    return { status, headers, body, url: finalURL };
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }
}

function adaptExternalPriceSource(source, payload, options) {
  if (source === "genai-prices") return priceCardsFromGenAIPrices(payload, options);
  if (source === "models.dev") return priceCardsFromModelsDev(payload, options);
  if (source === "litellm") return priceCardsFromLiteLLM(payload, options);
  if (source === "openrouter") return priceCardsFromOpenRouterModels(payload, options);
  throw new Error(`unsupported external price source: ${source}`);
}

async function resolveExternalSourceState(source, options) {
  const { cacheKey, data: cache } = await readResolverCache(options.cacheDir, source, options.url);
  const age = cache ? resolverCacheAge(cache, options.now) : null;
  const state = { name: source, type: "external", url: options.url, cache_key: cacheKey, status: "unavailable", card_count: cache?.price_cards?.length || 0 };
  if (cache) {
    ["retrieved_at", "validated_at", "checksum", "etag", "last_modified"].forEach((key) => {
      if (cache.source[key]) state[key] = cache.source[key];
    });
  }
  if (options.offline) {
    if (cache) {
      state.status = age !== null && age <= options.maxAgeSeconds ? "cache_fresh" : "cache_stale";
      state.priceCards = cache.price_cards;
      return { state, warnings: [] };
    }
    return { state, warnings: [resolverSourceWarning("price_source_unavailable", source, "offline_cache_miss")] };
  }
  if (cache && !options.refresh && age !== null && age <= options.maxAgeSeconds) {
    state.status = "cache_fresh";
    state.priceCards = cache.price_cards;
    return { state, warnings: [] };
  }
  const conditionalHeaders = {};
  if (cache?.source?.etag) conditionalHeaders["If-None-Match"] = cache.source.etag;
  if (cache?.source?.last_modified) conditionalHeaders["If-Modified-Since"] = cache.source.last_modified;
  try {
    const response = await fetchResolverSource(options.url, { ...options, headers: conditionalHeaders });
    const checkedAt = resolverTimestamp(options.now);
    if (response.status === 304) {
      if (!cache) throw new Error("received 304 without a cached representation");
      cache.source.validated_at = checkedAt;
      cache.source.etag = response.headers.etag || cache.source.etag;
      cache.source.last_modified = response.headers["last-modified"] || cache.source.last_modified;
      atomicWriteResolverCache(options.cacheDir, cacheKey, cache);
      Object.assign(state, { status: "cache_validated", validated_at: checkedAt, etag: cache.source.etag, last_modified: cache.source.last_modified, priceCards: cache.price_cards });
      return { state, warnings: [] };
    }
    if (response.status < 200 || response.status >= 300) throw new Error(`price source returned HTTP ${response.status}`);
    const payload = JSON.parse(new TextDecoder().decode(response.body));
    const priceCards = JSON.parse(JSON.stringify(adaptExternalPriceSource(source, payload, {
      sourceUrl: response.url, source_url: response.url, retrievedAt: checkedAt, retrieved_at: checkedAt
    })));
    if (!priceCards.length) throw new Error("price source produced no supported price cards");
    const envelope = {
      schema_version: "0.1",
      source: { name: source, type: "external", url: options.url, resolved_url: response.url, retrieved_at: checkedAt, validated_at: checkedAt, checksum: await resolverChecksum(response.body) },
      cards_checksum: await resolverChecksum(stableStringify(priceCards)),
      price_cards: priceCards
    };
    if (response.headers.etag) envelope.source.etag = response.headers.etag;
    if (response.headers["last-modified"]) envelope.source.last_modified = response.headers["last-modified"];
    atomicWriteResolverCache(options.cacheDir, cacheKey, envelope);
    Object.assign(state, {
      status: "refreshed", retrieved_at: checkedAt, validated_at: checkedAt, checksum: envelope.source.checksum,
      etag: envelope.source.etag, last_modified: envelope.source.last_modified, card_count: priceCards.length, priceCards
    });
    return { state, warnings: [] };
  } catch {
    if (cache) {
      state.status = "cache_stale";
      state.priceCards = cache.price_cards;
      return { state, warnings: [resolverSourceWarning("price_source_refresh_failed", source, "last_known_good")] };
    }
    return { state, warnings: [resolverSourceWarning("price_source_unavailable", source, "fetch_failed")] };
  }
}

function externalSourceOrder(provider, requestedSources) {
  const raw = requestedSources !== undefined
    ? [...requestedSources].map(String)
    : String(provider || "").toLowerCase() === "openrouter"
      ? [...OPENROUTER_EXTERNAL_PRICE_SOURCES]
      : [...DEFAULT_EXTERNAL_PRICE_SOURCES];
  const result = [];
  raw.forEach((source) => {
    if (!Object.hasOwn(EXTERNAL_PRICE_SOURCE_URLS, source)) throw new Error(`unsupported external price source: ${source}`);
    if (!result.includes(source)) result.push(source);
  });
  if (!result.length) throw new Error("at least one external price source is required");
  return result;
}

function externalCandidateQuality(usageLedger, priceCards) {
  const ledger = calculateCost({ usageLedger, priceCards: compiledExternalPriceCatalog(priceCards) });
  const codes = new Set((ledger.warnings || []).map((warning) => String(warning.code)));
  return { complete: ![...codes].some((code) => INCOMPLETE_PRICE_WARNING_CODES.has(code)), pricedComponents: (ledger.components || []).length };
}

export async function resolvePriceCatalog(options = {}) {
  const explicitCards = options.contractPriceCards ?? options.contract_price_cards ?? options.priceCards ?? options.price_cards;
  const now = resolverNow(options.now);
  if (explicitCards !== undefined) {
    const cards = Array.isArray(explicitCards) ? explicitCards : [...explicitCards];
    return {
      schema_version: "0.1", selected_source: "user", price_cards: cards,
      sources: [{ name: "user", type: options.contractPriceCards !== undefined || options.contract_price_cards !== undefined ? "contract" : "user", status: "selected", card_count: cards.length }],
      warnings: [], resolved_at: resolverTimestamp(now)
    };
  }
  const usageLedger = options.usageLedger ?? options.usage_ledger;
  const provider = options.provider || usageLedger?.provider;
  const order = externalSourceOrder(provider, options.sources ?? options.priceSources ?? options.price_sources);
  const sourceURLs = { ...EXTERNAL_PRICE_SOURCE_URLS, ...(options.sourceUrls || options.source_urls || {}) };
  const cacheDir = options.cacheDir || options.cache_dir || defaultPriceCacheDir();
  const maxAgeSeconds = Number(options.maxAgeSeconds ?? options.max_age_seconds ?? DEFAULT_PRICE_CACHE_MAX_AGE_SECONDS);
  if (!Number.isFinite(maxAgeSeconds) || maxAgeSeconds < 0) throw new Error("maxAgeSeconds must be a non-negative number");
  const sourceStates = [];
  const operationalWarnings = [];
  let firstPartial = null;
  let selected = null;
  for (const source of order) {
    const resolved = await resolveExternalSourceState(source, {
      url: sourceURLs[source], cacheDir, offline: Boolean(options.offline), refresh: Boolean(options.refresh), maxAgeSeconds,
      timeoutMs: Number(options.timeoutMs ?? options.timeout_ms ?? 15000), maxBytes: Number(options.maxBytes ?? options.max_bytes ?? 64 * 1024 * 1024),
      fetcher: options.fetcher, now
    });
    const priceCards = resolved.state.priceCards || [];
    delete resolved.state.priceCards;
    sourceStates.push(resolved.state);
    operationalWarnings.push(...resolved.warnings);
    if (!priceCards.length) continue;
    if (!usageLedger) { selected = { source, priceCards }; break; }
    const quality = externalCandidateQuality(usageLedger, priceCards);
    resolved.state.priced_component_count = quality.pricedComponents;
    resolved.state.applicable = quality.pricedComponents > 0;
    if (quality.pricedComponents > 0 && !firstPartial) firstPartial = { source, priceCards };
    if (quality.complete) { selected = { source, priceCards }; break; }
  }
  selected ||= firstPartial;
  sourceStates.forEach((state) => { state.selected = state.name === selected?.source; });
  if (!selected) operationalWarnings.push({
    code: "price_source_unavailable", message: "No configured external price source produced applicable price cards.",
    metadata: { source: order.join(","), status: "no_applicable_source" }
  });
  const seen = new Set();
  const warnings = operationalWarnings.filter((warning) => {
    const key = `${warning.code}\0${warning.metadata.source}\0${warning.metadata.status}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return {
    schema_version: "0.1", selected_source: selected?.source || null, price_cards: selected?.priceCards || [],
    sources: sourceStates, warnings, resolved_at: resolverTimestamp(now)
  };
}

function priceResolutionMetadata(resolution) {
  return {
    schema_version: resolution.schema_version || "0.1",
    selected_source: resolution.selected_source,
    sources: resolution.sources || [],
    resolved_at: resolution.resolved_at
  };
}

export function attachPriceResolution(result, resolution) {
  result.metadata = { ...(result.metadata || {}), price_resolution: priceResolutionMetadata(resolution) };
  const warnings = [...(result.warnings || [])];
  const existing = new Set(warnings.map((warning) => `${warning.code}\0${stableStringify(warning.metadata || {})}`));
  (resolution.warnings || []).forEach((warning) => {
    const key = `${warning.code}\0${stableStringify(warning.metadata || {})}`;
    if (!existing.has(key)) {
      warnings.push({ ...warning });
      existing.add(key);
    }
  });
  result.warnings = warnings;
  return result;
}

const RESOLVER_OPTION_NAMES = new Map([
  ["contractPriceCards", "contractPriceCards"], ["contract_price_cards", "contractPriceCards"],
  ["sources", "sources"], ["priceSources", "sources"], ["price_sources", "sources"],
  ["sourceUrls", "sourceUrls"], ["source_urls", "sourceUrls"],
  ["cacheDir", "cacheDir"], ["cache_dir", "cacheDir"], ["offline", "offline"],
  ["refresh", "refresh"], ["maxAgeSeconds", "maxAgeSeconds"], ["max_age_seconds", "maxAgeSeconds"],
  ["timeoutMs", "timeoutMs"], ["timeout_ms", "timeoutMs"], ["maxBytes", "maxBytes"],
  ["max_bytes", "maxBytes"], ["fetcher", "fetcher"], ["now", "now"]
]);

function splitResolverOptions(options) {
  const calculation = { ...options };
  const resolver = {};
  RESOLVER_OPTION_NAMES.forEach((target, source) => {
    if (Object.hasOwn(calculation, source)) {
      resolver[target] = calculation[source];
      delete calculation[source];
    }
  });
  return { calculation, resolver };
}

export async function fromResponseAuto(response, options = {}) {
  const { calculation, resolver } = splitResolverOptions(options);
  const explicitCards = calculation.priceCards ?? calculation.price_cards;
  delete calculation.priceCards;
  delete calculation.price_cards;
  if (explicitCards !== undefined) {
    const resolution = await resolvePriceCatalog({ ...resolver, priceCards: explicitCards });
    return attachPriceResolution(fromResponse(response, { ...calculation, priceCards: compiledExternalPriceCatalog(resolution.price_cards) }), resolution);
  }
  const resolvedOptions = { ...calculation, surface: calculation.surface || inferSurface(response, calculation) || "unknown" };
  let usageLedger;
  try {
    usageLedger = extractUsageLedger(response, resolvedOptions);
  } catch {
    return fromResponse(response, { ...calculation, priceCards: [] });
  }
  const resolution = await resolvePriceCatalog({ ...resolver, usageLedger, provider: usageLedger.provider });
  return attachPriceResolution(fromResponse(response, { ...calculation, priceCards: compiledExternalPriceCatalog(resolution.price_cards) }), resolution);
}

export async function fromBatchResultsAuto(items, options = {}) {
  const { calculation, resolver } = splitResolverOptions(options);
  const explicitCards = calculation.priceCards ?? calculation.price_cards;
  delete calculation.priceCards;
  delete calculation.price_cards;
  const resolution = await resolvePriceCatalog({ ...resolver, provider: calculation.provider, priceCards: explicitCards });
  const result = fromBatchResults(items, { ...calculation, priceCards: compiledExternalPriceCatalog(resolution.price_cards) });
  result.metadata = { ...(result.metadata || {}), price_resolution: priceResolutionMetadata(resolution) };
  attachPriceResolution(result.aggregate, resolution);
  (result.items || []).forEach((item) => {
    if (item.ledger) attachPriceResolution(item.ledger, resolution);
  });
  const existing = new Set((result.warnings || []).map((warning) => `${warning.code}\0${stableStringify(warning.metadata || {})}`));
  (resolution.warnings || []).forEach((warning) => {
    const key = `${warning.code}\0${stableStringify(warning.metadata || {})}`;
    if (!existing.has(key)) {
      result.warnings.push({ ...warning });
      existing.add(key);
    }
  });
  return result;
}

export async function fromOTelGenAISpanAuto(span, options = {}) {
  const { calculation, resolver } = splitResolverOptions(options);
  const explicitCards = calculation.priceCards ?? calculation.price_cards;
  delete calculation.priceCards;
  delete calculation.price_cards;
  const usageLedger = usageLedgerFromOTelGenAISpan(span, calculation);
  const resolution = await resolvePriceCatalog({ ...resolver, provider: usageLedger.provider, usageLedger, priceCards: explicitCards });
  return attachPriceResolution(fromOTelGenAISpan(span, { ...calculation, priceCards: compiledExternalPriceCatalog(resolution.price_cards) }), resolution);
}

export async function estimateCostAuto(options = {}) {
  const { calculation, resolver } = splitResolverOptions(options);
  const explicitCards = calculation.priceCards ?? calculation.price_cards;
  delete calculation.priceCards;
  delete calculation.price_cards;
  const rawComponents = Array.isArray(calculation.components)
    ? calculation.components
    : Object.entries(calculation.components || {}).map(([name, quantity]) => ({ name, quantity }));
  const usageLedger = {
    schema_version: "0.1",
    provider: calculation.provider,
    surface: calculation.surface,
    model: { requested: calculation.model, returned: calculation.model, billed: calculation.model, alias_resolution: "none" },
    components: rawComponents.map((component) => ({
      name: String(component.name), quantity: normalizeDecimalString(component.quantity || 0), unit: component.unit || "token"
    }))
  };
  if (calculation.context) usageLedger.context = { ...calculation.context };
  const resolution = await resolvePriceCatalog({ ...resolver, provider: calculation.provider, usageLedger, priceCards: explicitCards });
  return attachPriceResolution(estimateCost({ ...calculation, priceCards: compiledExternalPriceCatalog(resolution.price_cards) }), resolution);
}

export async function priceCacheStatus(options = {}) {
  const cacheDir = options.cacheDir || options.cache_dir || defaultPriceCacheDir();
  const now = resolverNow(options.now);
  const entries = [];
  if (!nodeRuntimeAvailable() || String(cacheDir).startsWith("memory://")) {
    for (const [key, raw] of [...EXTERNAL_PRICE_MEMORY_CACHE.entries()].sort(([left], [right]) => left.localeCompare(right))) {
      if (!key.startsWith(`${cacheDir}/`)) continue;
      const data = clonePriceValue(raw);
      const age = resolverCacheAge(data, now);
      entries.push({
        cache_key: key.slice(String(cacheDir).length + 1), name: data.source?.name, url: data.source?.url,
        retrieved_at: data.source?.retrieved_at, validated_at: data.source?.validated_at,
        checksum: data.source?.checksum, etag: data.source?.etag, last_modified: data.source?.last_modified,
        card_count: data.price_cards?.length || 0, age_seconds: age === null ? null : Math.floor(age), status: "valid"
      });
    }
  } else if (fs.existsSync(cacheDir)) {
    for (const cacheKey of fs.readdirSync(cacheDir).filter((name) => name.endsWith(".json")).sort()) {
      try {
        const data = JSON.parse(fs.readFileSync(path.join(cacheDir, cacheKey), "utf8"));
        const age = resolverCacheAge(data, now);
        const valid = data?.source && Array.isArray(data.price_cards);
        entries.push({
          cache_key: cacheKey, name: data?.source?.name, url: data?.source?.url,
          retrieved_at: data?.source?.retrieved_at, validated_at: data?.source?.validated_at,
          checksum: data?.source?.checksum, etag: data?.source?.etag, last_modified: data?.source?.last_modified,
          card_count: Array.isArray(data?.price_cards) ? data.price_cards.length : 0,
          age_seconds: age === null ? null : Math.floor(age), status: valid ? "valid" : "invalid"
        });
      } catch {
        entries.push({ cache_key: cacheKey, status: "invalid" });
      }
    }
  }
  return { schema_version: "0.1", cache_dir: cacheDir, checked_at: resolverTimestamp(now), entries };
}

export async function clearPriceCache(options = {}) {
  const cacheDir = options.cacheDir || options.cache_dir || defaultPriceCacheDir();
  const requested = options.sources ? new Set([...options.sources].map(String)) : null;
  const removed = [];
  const selected = (cacheKey) => {
    const source = cacheKey.replace(/-[0-9a-f]{12}\.json$/, "");
    return !requested || requested.has(source);
  };
  if (!nodeRuntimeAvailable() || String(cacheDir).startsWith("memory://")) {
    for (const key of [...EXTERNAL_PRICE_MEMORY_CACHE.keys()]) {
      const cacheKey = key.slice(String(cacheDir).length + 1);
      if (key.startsWith(`${cacheDir}/`) && selected(cacheKey)) {
        EXTERNAL_PRICE_MEMORY_CACHE.delete(key);
        removed.push(cacheKey);
      }
    }
  } else if (fs.existsSync(cacheDir)) {
    for (const cacheKey of fs.readdirSync(cacheDir).filter((name) => name.endsWith(".json")).sort()) {
      if (!selected(cacheKey)) continue;
      const filePath = path.join(cacheDir, cacheKey);
      fs.unlinkSync(filePath);
      EXTERNAL_PRICE_DISK_CACHE.delete(filePath);
      removed.push(cacheKey);
    }
  }
  return { schema_version: "0.1", cache_dir: cacheDir, removed };
}

export function canonicalJSONString(value) {
  return `${stableStringify(value)}\n`;
}

export async function sha256Bytes(value) {
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
  if (!globalThis.crypto || !globalThis.crypto.subtle) throw new Error("Web Crypto SHA-256 is unavailable in this runtime");
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((part) => part.toString(16).padStart(2, "0")).join("");
}

export async function verifyCatalogManifest(manifest, artifacts = {}) {
  const entries = [manifest && manifest.catalog, ...(manifest && Array.isArray(manifest.shards) ? manifest.shards : [])];
  const checked = [];
  let valid = Boolean(
    manifest && manifest.schema_version === "0.1" && manifest.algorithm === "sha256" &&
    manifest.catalog && typeof manifest.catalog === "object" && Array.isArray(manifest.shards)
  );
  for (const entry of entries) {
    if (!entry || typeof entry !== "object" || !entry.path || typeof entry.sha256 !== "string" || entry.sha256.length !== 64) {
      valid = false;
      checked.push({ path: entry && entry.path ? String(entry.path) : "", exists: false, sha256: null, matches: false });
      continue;
    }
    const value = artifacts[entry.path];
    const exists = value !== undefined;
    const digest = exists ? await sha256Bytes(value) : null;
    const matches = exists && digest === entry.sha256;
    valid = valid && matches;
    checked.push({ path: entry.path, exists, sha256: digest, matches });
  }
  return { schema_version: "0.1", valid, algorithm: "sha256", artifacts: checked };
}
