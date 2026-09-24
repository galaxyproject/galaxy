import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";

import { type RecentPaletteItem, useRecentPaletteItems } from "@/composables/useRecentPaletteItems";

import type { PaletteItem } from "../types";
import { rankPaletteItems } from "../utilities";

/** How one provider renders the entities the palette remembers */
export interface RecentRows {
    /** MRU bucket, see `useRecentPaletteItems` */
    type: string;
    /** Row built from the store's current copy of the entity, unset where no store holds it */
    stored?(entry: RecentPaletteItem): PaletteItem | undefined;
    /** Row of an entity no store holds; the remembered name and route fill in the rest */
    fallback(entry: RecentPaletteItem): { id: string; icon: IconDefinition; title?: string; to: string };
}

/**
 * The remembered entities of one type matching `query`, most recently used
 * first: the store's copy renders current names and dates where it still holds
 * one, and a row built from what the palette remembered stands in otherwise.
 */
export function recentPaletteItems(rows: RecentRows, query: string, limit: number): PaletteItem[] {
    const { recentItems } = useRecentPaletteItems();
    const items = recentItems(rows.type).map((entry) => {
        const stored = rows.stored?.(entry);
        if (stored) {
            return stored;
        }
        const { id, icon, title, to } = rows.fallback(entry);
        return { id, icon, mru: { type: rows.type, id: entry.id }, title: title ?? entry.name, to: entry.to ?? to };
    });
    return rankPaletteItems(items, query).slice(0, limit);
}
