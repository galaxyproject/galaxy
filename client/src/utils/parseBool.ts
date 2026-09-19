/**
 * Parses a value to a boolean.
 * Returns true for boolean `true` or the string `"true"` (case-insensitive).
 * Returns false for everything else.
 */
export function parseBool(value: unknown): boolean {
    if (typeof value === "boolean") {
        return value;
    }
    if (typeof value === "string") {
        return value.toLowerCase() === "true";
    }
    return false;
}
