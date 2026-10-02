/**
 * Filters `items` to those whose `label` contains `query` (case-insensitive) and
 * orders them by match quality: exact matches first, then prefix matches, then
 * any other substring matches. The original order is preserved within each tier,
 * so an alphabetically sorted list stays alphabetical inside each group.
 *
 * An empty or whitespace-only query returns `items` unchanged.
 */
export function rankBySearch<T>(items: T[], query: string | null | undefined, label: keyof T): T[] {
    const normalizedQuery = (query ?? "").trim().toLowerCase();
    if (!normalizedQuery) {
        return items;
    }
    const exact: T[] = [];
    const prefix: T[] = [];
    const contains: T[] = [];
    for (const item of items) {
        const text = String(item[label] ?? "").toLowerCase();
        if (text === normalizedQuery) {
            exact.push(item);
        } else if (text.startsWith(normalizedQuery)) {
            prefix.push(item);
        } else if (text.includes(normalizedQuery)) {
            contains.push(item);
        }
    }
    return [...exact, ...prefix, ...contains];
}
