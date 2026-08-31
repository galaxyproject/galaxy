import { faChartBar } from "@fortawesome/free-solid-svg-icons";
import { format } from "date-fns";

import type { VisualizationSummary } from "@/api/visualizations";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { useVisualizationStore } from "@/stores/visualizationStore";
import { galaxyTimeToDate } from "@/utils/dates";

import type { CommandPaletteProvider, PaletteItem, ScopedSection } from "../types";
import { rankPaletteItems } from "../utilities";
import { markListRefreshed, refreshListWhenStale } from "./refresh";

/** Entity type used for the palette MRU list of visualizations */
export const VISUALIZATION_RECENT_TYPE = "visualization";

/** Only the saved visualizations of the current user are searchable (`v:`) */
const VARIANT = "my";

/** Identity of the cached list in the palette's refresh bookkeeping */
const REFRESH_KEY = "visualizations:my";

/** Cap of a single rendered section */
const MAX_RESULTS = 8;
const MAX_RECENT = 5;

/** Same click target the saved visualizations grid uses to open an item */
export function visualizationDisplayPath(visualization: { id: string; type?: string | null }): string {
    const type = visualization.type ?? "";
    return `/visualizations/display?visualization=${encodeURIComponent(type)}&visualization_id=${encodeURIComponent(
        visualization.id,
    )}`;
}

/** "Aug 31, 2026", or nothing when the backend sent no (or a broken) date */
function formatUpdated(updateTime: string | null | undefined): string {
    if (!updateTime) {
        return "";
    }
    try {
        return format(galaxyTimeToDate(updateTime), "MMM d, yyyy");
    } catch {
        return "";
    }
}

function visualizationToItem(visualization: VisualizationSummary): PaletteItem {
    return {
        id: `visualizations:${visualization.id}`,
        icon: faChartBar,
        keywords: visualization.type,
        mru: { type: VISUALIZATION_RECENT_TYPE, id: visualization.id },
        subtitle: [visualization.type, formatUpdated(visualization.update_time)].filter(Boolean).join(" · "),
        title: visualization.title,
        to: visualizationDisplayPath(visualization),
    };
}

/** Drops repeated ids, keeping the first (better ranked) occurrence */
function dedupeById(items: PaletteItem[]): PaletteItem[] {
    const seen = new Set<string>();
    return items.filter((item) => {
        if (seen.has(item.id)) {
            return false;
        }
        seen.add(item.id);
        return true;
    });
}

/**
 * Hydrates the saved visualizations once per session and refreshes them in the
 * background afterwards, so a long lived tab does not keep serving the list it
 * saw first (see `refresh.ts`).
 */
async function ensureHydrated(): Promise<void> {
    const store = useVisualizationStore();
    if (!store.hasLoadedVariant(VARIANT)) {
        await store.ensureVariantLoaded(VARIANT);
        markListRefreshed(REFRESH_KEY);
    } else {
        refreshListWhenStale(REFRESH_KEY, () => store.fetchVisualizations(VARIANT));
    }
}

/**
 * Store-first search: rank whatever the store already cached, and only ask the
 * backend when the cache cannot fill the section. Backend results are merged
 * into the same store, so the two sources dedupe by id.
 *
 * @param cacheOnly never request anything, not even to hydrate an empty cache —
 * the unscoped root fan-out runs on every provider at once and only filters what
 * the stores already hold; the `v:` scope does the fetching.
 */
async function searchVisualizations(query: string, limit = MAX_RESULTS, cacheOnly = false): Promise<PaletteItem[]> {
    const store = useVisualizationStore();
    if (!cacheOnly) {
        await ensureHydrated();
    }
    const cached = rankPaletteItems(store.getVisualizations(VARIANT).map(visualizationToItem), query);
    if (cacheOnly || !query || cached.length >= limit) {
        return cached.slice(0, limit);
    }
    const fetched = await store.fetchVisualizations(VARIANT, { search: query, limit });
    return dedupeById([...cached, ...fetched.map(visualizationToItem)]).slice(0, limit);
}

/** Latest visualizations of the user, newest first, straight from the cache */
function latestItems(limit = MAX_RESULTS): PaletteItem[] {
    const store = useVisualizationStore();
    return store.getVisualizations(VARIANT).slice(0, limit).map(visualizationToItem);
}

/** Visualizations opened through the palette before, most recent first */
function recentItems(limit = MAX_RECENT): PaletteItem[] {
    const store = useVisualizationStore();
    const { recentItems: recent } = useRecentPaletteItems();
    return recent(VISUALIZATION_RECENT_TYPE)
        .slice(0, limit)
        .map((entry) => {
            // prefer the cached summary, which carries a current type and date
            const cachedSummary = store.getVisualizationSummary(entry.id);
            return cachedSummary
                ? visualizationToItem(cachedSummary)
                : {
                      id: `visualizations:${entry.id}`,
                      icon: faChartBar,
                      mru: { type: VISUALIZATION_RECENT_TYPE, id: entry.id },
                      title: entry.name,
                      to: entry.to ?? visualizationDisplayPath({ id: entry.id }),
                  };
        });
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
    /** Root mode fan-out, ranking the cached visualizations without a request */
    async search(query: string) {
        const trimmed = query.trim();
        if (!trimmed) {
            return latestItems();
        }
        return searchVisualizations(trimmed, MAX_RESULTS, true);
    },
    async searchScoped(_scope, query: string): Promise<ScopedSection[]> {
        const trimmed = query.trim();
        if (!trimmed) {
            await ensureHydrated();
            return sectionsWithItems([
                { id: "recent", items: recentItems(), title: "Recent" },
                { id: "latest", items: latestItems(), title: "Latest visualizations" },
            ]);
        }
        const items = await searchVisualizations(trimmed);
        return sectionsWithItems([{ id: "results", items, title: "Visualizations" }]);
    },
};
