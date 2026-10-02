/**
 * Filters `items` to those where one of the `keys` values contains `query` (case-insensitive)
 * and orders them by their best match: exact matches first, then prefix matches, then
 * any other substring matches. The original order is preserved within each tier,
 * so an alphabetically sorted list stays alphabetical inside each group.
 *
 * An empty or whitespace-only query returns `items` unchanged.
 */
export function rankBySearch<T>(items: T[], query: string | null | undefined, keys: keyof T | (keyof T)[]): T[] {
    const normalizedQuery = (query ?? "").trim().toLowerCase();
    if (!normalizedQuery) {
        return items;
    }
    const searchKeys = Array.isArray(keys) ? keys : [keys];
    const exact: T[] = [];
    const prefix: T[] = [];
    const contains: T[] = [];
    for (const item of items) {
        const texts = searchKeys.map((key) => String(item[key] ?? "").toLowerCase());
        if (texts.some((text) => text === normalizedQuery)) {
            exact.push(item);
        } else if (texts.some((text) => text.startsWith(normalizedQuery))) {
            prefix.push(item);
        } else if (texts.some((text) => text.includes(normalizedQuery))) {
            contains.push(item);
        }
    }
    return [...exact, ...prefix, ...contains];
}
