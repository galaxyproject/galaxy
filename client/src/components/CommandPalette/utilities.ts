import { type SearchCommonKeys, searchObjectsByKeys } from "@/components/Panels/utilities";

import { ACTIONS_SCOPE, findScope, type ScopeDefinition } from "./providers/scopes";
import type { PaletteItem } from "./types";

/** A scope token: one or two letters followed by a colon, e.g. `w:` or `hs:` */
const SCOPE_TOKEN = /^([a-zA-Z]{1,2}):(.*)$/;

const PALETTE_SEARCH_KEYS: SearchCommonKeys = {
    exact: 5,
    startsWith: 4,
    name: 3,
    description: 2,
    combined: 1,
    wordMatch: 0,
};

export type ParsedPaletteQuery =
    /** Unscoped search text */
    | { type: "text"; query: string }
    /** A recognized `>` or `x:` token, stripped from the remaining query */
    | { type: "scope"; scope: ScopeDefinition; query: string }
    /** A lone `?`, which opens the help panel */
    | { type: "help" };

/**
 * Classifies a raw palette query. `>` scopes to actions and an exactly
 * matching `x:`/`xy:` token scopes to that entity; anything else — including
 * unknown tokens such as `name:fastqc` — stays plain search text.
 */
export function parsePaletteQuery(raw: string): ParsedPaletteQuery {
    const trimmed = raw.trim();
    if (trimmed === "?") {
        return { type: "help" };
    }
    if (trimmed.startsWith(">")) {
        return { type: "scope", scope: ACTIONS_SCOPE, query: trimmed.slice(1).trim() };
    }
    const token = trimmed.match(SCOPE_TOKEN);
    const scope = token ? findScope(token[1] as string) : undefined;
    if (token && scope) {
        return { type: "scope", scope, query: (token[2] as string).trim() };
    }
    return { type: "text", query: trimmed };
}

/**
 * Whether the text still reads as a scope token — `w:`, or the `xy:` of a scope
 * this instance does not offer. Such a token is a filter the user is typing, not
 * something worth sending to a backend as a search term.
 */
export function isScopeTokenLike(text: string): boolean {
    return SCOPE_TOKEN.test(text.trim());
}

export interface ScoredPaletteItem {
    item: PaletteItem;
    /** Match quality from the shared scorer, higher is better */
    order: number;
}

/**
 * Scores palette items against a query, reusing the tool panel's weighted
 * scorer. Items that do not match are dropped; an empty query returns all
 * items unchanged with a neutral score.
 */
export function scorePaletteItems(items: PaletteItem[], query: string): ScoredPaletteItem[] {
    if (!query.trim()) {
        return items.map((item) => ({ item, order: 0 }));
    }
    const records = items.map((item) => ({
        id: item.id,
        name: item.title.toLowerCase(),
        description: [item.subtitle, item.keywords].filter(Boolean).join(" ").toLowerCase(),
    }));
    const { matchedResults } = searchObjectsByKeys(records, PALETTE_SEARCH_KEYS, query, ["name", "description"]);
    const itemsById = new Map(items.map((item) => [item.id, item]));
    return matchedResults
        .sort((a, b) => b.order - a.order)
        .flatMap((match) => {
            const item = itemsById.get(match.id);
            return item ? [{ item, order: match.order }] : [];
        });
}

/** Like {@link scorePaletteItems}, returning only the ordered items */
export function rankPaletteItems(items: PaletteItem[], query: string): PaletteItem[] {
    return scorePaletteItems(items, query).map((scored) => scored.item);
}
