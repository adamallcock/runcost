import { InvalidUsageError } from "./contracts.js";

const MONEY_PRECISION = 18n;
export function normalizeDecimalString(value) {
  if (value === null || value === undefined) {
    return "0";
  }
  if (typeof value === "number" && !Number.isFinite(value)) {
    throw new InvalidUsageError(`invalid decimal: ${value}`);
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
    throw new InvalidUsageError(`invalid decimal: ${value}`);
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

export function parseDecimal(value) {
  const text = normalizeDecimalString(value);
  if (!/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(text)) {
    throw new InvalidUsageError(`invalid decimal: ${value}`);
  }
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

export function canonicalDecimal(value) {
  const parsed = parseDecimal(value);
  return formatDecimal(parsed.value, parsed.scale);
}

export function pow10(scale) {
  return 10n ** BigInt(scale);
}

export function roundDivideHalfEven(numerator, denominator) {
  if (denominator === 0n) throw new Error("division by zero");
  const negative = (numerator < 0n) !== (denominator < 0n);
  const absoluteNumerator = numerator < 0n ? -numerator : numerator;
  const absoluteDenominator = denominator < 0n ? -denominator : denominator;
  let quotient = absoluteNumerator / absoluteDenominator;
  const remainder = absoluteNumerator % absoluteDenominator;
  const comparison = remainder * 2n - absoluteDenominator;
  if (comparison > 0n || (comparison === 0n && quotient % 2n !== 0n)) {
    quotient += 1n;
  }
  return negative ? -quotient : quotient;
}

export function formatDecimal(value, scale) {
  if (scale > MONEY_PRECISION) {
    value = roundDivideHalfEven(value, pow10(scale - MONEY_PRECISION));
    scale = MONEY_PRECISION;
  }
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

export function addDecimal(left, right) {
  const a = parseDecimal(left);
  const b = parseDecimal(right);
  const scale = a.scale > b.scale ? a.scale : b.scale;
  const av = a.value * pow10(scale - a.scale);
  const bv = b.value * pow10(scale - b.scale);
  return formatDecimal(av + bv, scale);
}

export function subtractDecimal(left, right) {
  const a = parseDecimal(left);
  const b = parseDecimal(right);
  const scale = a.scale > b.scale ? a.scale : b.scale;
  const av = a.value * pow10(scale - a.scale);
  const bv = b.value * pow10(scale - b.scale);
  return formatDecimal(av - bv, scale);
}

export function compareDecimal(left, right) {
  const a = parseDecimal(left);
  const b = parseDecimal(right);
  const scale = a.scale > b.scale ? a.scale : b.scale;
  const av = a.value * pow10(scale - a.scale);
  const bv = b.value * pow10(scale - b.scale);
  return av < bv ? -1 : av > bv ? 1 : 0;
}

export function multiplyDivideDecimal(quantity, amount, per) {
  const q = parseDecimal(quantity);
  const a = parseDecimal(amount);
  const p = parseDecimal(per);
  if (p.value <= 0n) {
    throw new Error("price.per must be greater than zero");
  }

  const numerator = q.value * a.value * pow10(p.scale) * pow10(MONEY_PRECISION);
  const denominator = p.value * pow10(q.scale + a.scale);
  return formatDecimal(roundDivideHalfEven(numerator, denominator), MONEY_PRECISION);
}

export function multiplyDecimal(left, right) {
  return multiplyDivideDecimal(left, right, "1");
}
