import { type SearchCommonKeys, searchObjectsByKeys } from "@/components/Panels/utilities";

import type { CommandPaletteProvider, PaletteItem } from "./types";

/**
 * Prefixes reserved for per-entity providers that are not implemented yet
 * (workflows, histories, datasets, visualizations, invocations, pages).
 */
export const RESERVED_PREFIXES = ["w", "h", "d", "v", "i", "p"];

const PALETTE_SEARCH_KEYS: SearchCommonKeys = {
    exact: 5,
    startsWith: 4,
    name: 3,
    description: 2,
    combined: 1,
    wordMatch: 0,
};

export interface ParsedPaletteQuery {
    /** Provider the query is scoped to; unset searches all providers */
    providerId?: string;
    query: string;
    /** Known entity prefix whose provider is not available yet */
    reservedPrefix?: string;
}

/**
 * Splits a raw palette query into an optional provider scope and the actual
 * search text. `>` scopes to actions; single-letter `x:` prefixes scope to
 * the provider registered for that letter.
 */
export function parsePaletteQuery(raw: string, providers: CommandPaletteProvider[]): ParsedPaletteQuery {
    const trimmed = raw.trim();
    if (trimmed.startsWith(">")) {
        return { providerId: "actions", query: trimmed.slice(1).trim() };
    }
    const prefixMatch = trimmed.match(/^([a-zA-Z]):(.*)$/);
    if (prefixMatch) {
        const prefix = (prefixMatch[1] as string).toLowerCase();
        const query = (prefixMatch[2] as string).trim();
        const provider = providers.find((p) => p.prefix === prefix);
        if (provider) {
            return { providerId: provider.id, query };
        }
        if (RESERVED_PREFIXES.includes(prefix)) {
            return { reservedPrefix: prefix, query };
        }
    }
    return { query: trimmed };
}

/**
 * Ranks palette items against a query, reusing the tool panel's weighted
 * scorer. Items that do not match are dropped; an empty query returns all
 * items unchanged.
 */
export function rankPaletteItems(items: PaletteItem[], query: string): PaletteItem[] {
    if (!query.trim()) {
        return items;
    }
    const records = items.map((item) => ({
        id: item.id,
        name: item.title.toLowerCase(),
        description: [item.subtitle, item.keywords]
            .filter(Boolean)
            .join(" ")
            .toLowerCase(),
    }));
    const { matchedResults } = searchObjectsByKeys(records, PALETTE_SEARCH_KEYS, query, ["name", "description"]);
    const itemsById = new Map(items.map((item) => [item.id, item]));
    return matchedResults
        .sort((a, b) => b.order - a.order)
        .map((match) => itemsById.get(match.id))
        .filter((item): item is PaletteItem => Boolean(item));
}
