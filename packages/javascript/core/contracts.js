export class UnsupportedSurfaceError extends Error {
  constructor(surface) {
    super(`Unsupported surface: ${surface}`);
    this.name = "UnsupportedSurfaceError";
    this.surface = surface;
  }
}

export class InvalidUsageError extends Error {
  constructor(message, path = "$.usage") {
    super(message);
    this.name = "InvalidUsageError";
    this.path = path;
  }
}

export function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(deepFreeze);
    Object.freeze(value);
  }
  return value;
}

export function readonlyMap(map) {
  const view = {
    get: (key) => map.get(key), has: (key) => map.has(key),
    get size() { return map.size; },
    entries: () => map.entries(), keys: () => map.keys(), values: () => map.values(),
    [Symbol.iterator]: () => map[Symbol.iterator](),
    forEach: (callback, thisArg) => map.forEach((value, key) => callback.call(thisArg, value, key, view))
  };
  return Object.freeze(view);
}
