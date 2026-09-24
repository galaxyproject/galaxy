import { faChartBar } from "@fortawesome/free-solid-svg-icons";

import type { VisualizationSummary } from "@/api/visualizations";
import { useVisualizationStore } from "@/stores/visualizationStore";
import { shortDateLabel } from "@/utils/dates";

import type { CommandPaletteProvider, PaletteItem, ScopedSection } from "../types";
import { PALETTE_LIMITS } from "./limits";
import { recentPaletteItems, type RecentRows } from "./recent";
import { ensureListHydrated, storeFirstItems, type StoreFirstList } from "./storeFirst";

/** Entity type used for the palette MRU list of visualizations */
export const VISUALIZATION_RECENT_TYPE = "visualization";

/** Only the saved visualizations of the current user are searchable (`v:`) */
const VARIANT = "my";

/** Same click target the saved visualizations grid uses to open an item */
export function visualizationDisplayPath(visualization: { id: string; type?: string | null }): string {
    const type = visualization.type ?? "";
    return `/visualizations/display?visualization=${encodeURIComponent(type)}&visualization_id=${encodeURIComponent(
        visualization.id,
    )}`;
}

function visualizationToItem(visualization: VisualizationSummary): PaletteItem {
    return {
        id: `visualizations:${visualization.id}`,
        icon: faChartBar,
        // the backend search also matches tags, and its rows are ranked locally
        keywords: [visualization.type, ...(visualization.tags ?? [])].join(" "),
        mru: { type: VISUALIZATION_RECENT_TYPE, id: visualization.id },
        subtitle: [visualization.type, shortDateLabel(visualization.update_time)].filter(Boolean).join(" · "),
        title: visualization.title,
        to: visualizationDisplayPath(visualization),
    };
}

/**
 * The user's saved visualizations, store first. The unfiltered fetch reports the
 * total, so a cache holding that many answers any query on its own.
 */
function visualizationList(): StoreFirstList {
    const store = useVisualizationStore();
    return {
        key: "visualizations:my",
        isLoaded: () => store.hasLoadedVariant(VARIANT),
        fetchListing: () => store.fetchVisualizations(VARIANT, { limit: PALETTE_LIMITS.page }),
        cachedItems: () => store.getVisualizations(VARIANT).map(visualizationToItem),
        isComplete: () =>
            store.hasLoadedVariant(VARIANT) &&
            store.getVisualizations(VARIANT).length >= store.totalMatchesByVariant[VARIANT],
        async searchItems(query) {
            const found = await store.fetchVisualizations(VARIANT, { search: query, limit: PALETTE_LIMITS.page });
            return found.map(visualizationToItem);
        },
    };
}

/** Latest visualizations of the user, newest first, straight from the cache */
function latestItems(limit = PALETTE_LIMITS.section): PaletteItem[] {
    const store = useVisualizationStore();
    return store.getVisualizations(VARIANT).slice(0, limit).map(visualizationToItem);
}

/** Visualizations opened through the palette before, most recent first */
function recentItems(limit = PALETTE_LIMITS.recent): PaletteItem[] {
    const store = useVisualizationStore();
    const rows: RecentRows = {
        type: VISUALIZATION_RECENT_TYPE,
        stored: (entry) => {
            // the cached summary carries a current type and date
            const summary = store.getVisualizationSummary(entry.id);
            return summary ? visualizationToItem(summary) : undefined;
        },
        fallback: (entry) => ({
            id: `visualizations:${entry.id}`,
            icon: faChartBar,
            to: visualizationDisplayPath({ id: entry.id }),
        }),
    };
    return recentPaletteItems(rows, "", limit);
}

function sectionsWithItems(sections: ScopedSection[]): ScopedSection[] {
    return sections.filter((section) => section.items.length > 0);
}

export const visualizationsProvider: CommandPaletteProvider = {
    id: "visualizations",
    title: "Visualizations",
    /** Cache-only, so the unscoped palette never fires a request on open */
    emptyQueryItems() {
        return latestItems();
    },
    /**
     * Root mode fan-out, ranking the cached visualizations without a request —
     * unlike the histories, workflows, reports and tools ones, which search the
     * backend there too; the `v:` scope does the fetching.
     */
    async search(query: string) {
        if (!query) {
            return latestItems();
        }
        return storeFirstItems(visualizationList(), query, PALETTE_LIMITS.section, { cacheOnly: true });
    },
    async searchScoped(_scope, query: string): Promise<ScopedSection[]> {
        if (!query) {
            await ensureListHydrated(visualizationList());
            return sectionsWithItems([
                { id: "recent", items: recentItems(), title: "Recent" },
                { id: "latest", items: latestItems(), title: "Latest visualizations" },
            ]);
        }
        const items = await storeFirstItems(visualizationList(), query, PALETTE_LIMITS.section);
        return sectionsWithItems([{ id: "results", items, title: "Visualizations" }]);
    },
};
