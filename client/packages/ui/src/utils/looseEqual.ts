/**
 * Group membership test, loose like BootstrapVue's: objects match by JSON form, other values by
 * string form, so a numeric option still matches a value that came back from the server as a string.
 * Stricter than BootstrapVue's: the JSON form depends on key order (`{ a, b }` does not match `{ b, a }`),
 * arrays match by JSON form, not item by item (`[1]` does not match `["1"]`), and null only matches null.
 */
export function looseEqual(a: unknown, b: unknown): boolean {
    if (a === b) {
        return true;
    }
    if (typeof a === "object" && a !== null && typeof b === "object" && b !== null) {
        return JSON.stringify(a) === JSON.stringify(b);
    }
    if (typeof a === "object" || typeof b === "object") {
        return false;
    }
    return String(a) === String(b);
}
