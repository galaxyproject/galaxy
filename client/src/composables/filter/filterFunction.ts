export type FilterField<O> = keyof O | string[];

export interface SearchIndexEntry<O> {
    item: O;
    /** Lower-cased string values of the searched fields. */
    values: string[];
}

const EXACT = 0;
const PREFIX = 1;
const CONTAINS = 2;
const NO_MATCH = 3;

function fieldValue<O extends object>(obj: O, field: FilterField<O>): unknown {
    if (Array.isArray(field)) {
        return field.reduce((acc: unknown, curr: string) => {
            if (acc && typeof acc === "object") {
                return (acc as Record<string, unknown>)[curr];
            }
            return undefined;
        }, obj);
    }
    return obj[field];
}

/**
 * Lower-cases the searched string values of every item once, so that `rankSearchIndex`
 * can be run for each new filter string without repeating that work.
 */
export function buildSearchIndex<O extends object>(arr: O[], fields: FilterField<O>[]): SearchIndexEntry<O>[] {
    return arr.map((item) => {
        const values: string[] = [];
        for (const field of fields) {
            const val = fieldValue(item, field);
            if (typeof val === "string") {
                values.push(val.toLowerCase());
            } else if (Array.isArray(val)) {
                for (const v of val) {
                    if (typeof v === "string") {
                        values.push(v.toLowerCase());
                    }
                }
            }
        }
        return { item, values };
    });
}

function matchTier(values: string[], query: string): number {
    let tier = NO_MATCH;
    for (const value of values) {
        if (value === query) {
            return EXACT;
        } else if (value.startsWith(query)) {
            tier = PREFIX;
        } else if (tier === NO_MATCH && value.includes(query)) {
            tier = CONTAINS;
        }
    }
    return tier;
}

/**
 * Returns the items with a searched value containing `filter` (case-insensitive,
 * surrounding whitespace ignored), ordered by their best match: exact matches first,
 * then prefix matches, then other substring matches. The original order is kept
 * within each group. An empty filter returns all items.
 */
export function rankSearchIndex<O>(index: SearchIndexEntry<O>[], filter: string): O[] {
    const query = filter.trim().toLowerCase();
    if (!query) {
        return index.map((entry) => entry.item);
    }
    const tiers: O[][] = [[], [], []];
    for (const entry of index) {
        const tier = matchTier(entry.values, query);
        if (tier !== NO_MATCH) {
            tiers[tier]!.push(entry.item);
        }
    }
    return tiers.flat();
}
