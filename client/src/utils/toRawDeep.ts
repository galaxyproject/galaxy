import { toRaw } from "vue";

/**
 * Vue 3's reactive values are proxies, which structuredClone() and
 * postMessage() can't copy, and toRaw() only unwraps the outermost one -- the
 * elements of a reactive array, or the nested objects of a reactive object,
 * are still proxies. Returns a copy with every level unwrapped. Plain objects,
 * arrays, Maps and Sets are copied; anything else is returned raw.
 */
export function toRawDeep<T>(value: T): T {
    return unwrap(value, new WeakMap()) as T;
}

/** structuredClone() for values that may hold reactive proxies at any depth. */
export function cloneRaw<T>(value: T): T {
    return structuredClone(toRawDeep(value));
}

function unwrap(value: unknown, seen: WeakMap<object, unknown>): unknown {
    const raw = toRaw(value);
    if (!raw || typeof raw !== "object") {
        return raw;
    }
    if (seen.has(raw)) {
        return seen.get(raw);
    }
    if (Array.isArray(raw)) {
        const copy: unknown[] = [];
        seen.set(raw, copy);
        raw.forEach((item) => copy.push(unwrap(item, seen)));
        return copy;
    }
    if (raw instanceof Map) {
        const copy = new Map();
        seen.set(raw, copy);
        raw.forEach((item, key) => copy.set(unwrap(key, seen), unwrap(item, seen)));
        return copy;
    }
    if (raw instanceof Set) {
        const copy = new Set();
        seen.set(raw, copy);
        raw.forEach((item) => copy.add(unwrap(item, seen)));
        return copy;
    }
    if (Object.getPrototypeOf(raw) === Object.prototype || Object.getPrototypeOf(raw) === null) {
        const copy: Record<string, unknown> = {};
        seen.set(raw, copy);
        Object.entries(raw).forEach(([key, item]) => (copy[key] = unwrap(item, seen)));
        return copy;
    }
    return raw;
}
