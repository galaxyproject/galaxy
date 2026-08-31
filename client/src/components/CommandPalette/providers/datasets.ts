import { faFile } from "@fortawesome/free-solid-svg-icons";

import type { HDASummary } from "@/api";
import { type RecentPaletteItem, useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { useDatasetListStore } from "@/stores/datasetListStore";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import type { CommandPaletteProvider, PaletteContext, PaletteItem, ScopedSection } from "../types";
import { rankPaletteItems } from "../utilities";
import { markListRefreshed, refreshListWhenStale } from "./refresh";

/** MRU bucket the palette records dataset selections under */
export const DATASET_RECENT_TYPE = "dataset";

/** Identity of the cached list in the palette's refresh bookkeeping */
const REFRESH_KEY = "datasets:latest";

/** Maximum number of rows rendered per section */
const SECTION_CAP = 6;
/** Shortest query worth a backend round trip; below it the cache answers alone */
const MIN_BACKEND_QUERY_LENGTH = 2;

/** Router location of a dataset preview */
function datasetRoute(id: string): string {
    return `/datasets/${id}/preview`;
}

/**
 * Extension, state and — when the owning history happens to be cached already —
 * its name. The history store is only read, never asked to fetch, so the
 * subtitle stays free of extra requests.
 */
function datasetSubtitle(dataset: HDASummary): string | undefined {
    const historyStore = useHistoryStore();
    const historyName = dataset.history_id ? historyStore.getHistoryById(dataset.history_id, false)?.name : undefined;
    const parts = [dataset.extension, dataset.state, historyName].filter(Boolean);
    return parts.length ? parts.join(" · ") : undefined;
}

function datasetToItem(dataset: HDASummary): PaletteItem {
    return {
        id: `datasets:${dataset.id}`,
        icon: faFile,
        mru: { type: DATASET_RECENT_TYPE, id: dataset.id },
        subtitle: datasetSubtitle(dataset),
        title: dataset.name || localize("Unnamed dataset"),
        to: datasetRoute(dataset.id),
    };
}

function recentToItem(entry: RecentPaletteItem): PaletteItem {
    return {
        id: `datasets:${entry.id}`,
        icon: faFile,
        mru: { type: DATASET_RECENT_TYPE, id: entry.id },
        title: entry.name || localize("Unnamed dataset"),
        to: entry.to ?? datasetRoute(entry.id),
    };
}

/** Most recently updated first; datasets without a timestamp sort last */
function byUpdateTimeDesc(a: HDASummary, b: HDASummary): number {
    const left = a.update_time ?? a.create_time ?? "";
    const right = b.update_time ?? b.create_time ?? "";
    return right.localeCompare(left);
}

/**
 * Whether the cached "latest" list is everything the backend has. The unfiltered
 * fetch reports the total, so a cache that reaches it can answer any query with
 * its local name filter and no search request is worth sending.
 */
function cacheHoldsEveryDataset(): boolean {
    const datasetListStore = useDatasetListStore();
    return (
        datasetListStore.hasLoadedLatest &&
        datasetListStore.latestDatasetIds.length >= datasetListStore.totalLatestMatches
    );
}

/**
 * Hydrates the "latest" list once per session and refreshes it in the background
 * afterwards, so a long lived tab does not keep serving the list it saw first.
 */
async function ensureLatestHydrated(): Promise<void> {
    const datasetListStore = useDatasetListStore();
    if (!datasetListStore.hasLoadedLatest) {
        await datasetListStore.ensureLatestLoaded();
        markListRefreshed(REFRESH_KEY);
    } else {
        refreshListWhenStale(REFRESH_KEY, () => datasetListStore.fetchDatasets());
    }
}

/**
 * Store-first dataset lookup: the cache answers every keystroke, and the
 * backend is only asked when the cache cannot produce a full section and does
 * not already hold every dataset. Fetched summaries are merged into the store,
 * so the next keystroke is local again.
 *
 * @param cacheOnly never request anything, not even to hydrate an empty cache —
 * the unscoped root fan-out runs on every provider at once and only filters what
 * the stores already hold; the `d:` scope does the fetching.
 */
async function matchingDatasets(query: string, cacheOnly = false): Promise<HDASummary[]> {
    const datasetListStore = useDatasetListStore();
    if (cacheOnly) {
        return datasetListStore.searchCachedDatasets(query, SECTION_CAP);
    }
    await ensureLatestHydrated();
    const cached = datasetListStore.searchCachedDatasets(query, SECTION_CAP);
    if (cached.length >= SECTION_CAP || query.length < MIN_BACKEND_QUERY_LENGTH || cacheHoldsEveryDataset()) {
        return cached;
    }
    await datasetListStore.fetchDatasets({ search: query, limit: SECTION_CAP });
    return datasetListStore.searchCachedDatasets(query, SECTION_CAP);
}

function recentItems(query: string): PaletteItem[] {
    const { recentItems: remembered } = useRecentPaletteItems();
    return rankPaletteItems(remembered(DATASET_RECENT_TYPE).map(recentToItem), query).slice(0, SECTION_CAP);
}

/** Drops items already shown in an earlier section */
function withoutItems(items: PaletteItem[], shown: PaletteItem[]): PaletteItem[] {
    const shownIds = new Set(shown.map((item) => item.id));
    return items.filter((item) => !shownIds.has(item.id));
}

function toSections(sections: ScopedSection[]): ScopedSection[] {
    return sections.filter((section) => section.items.length > 0);
}

export const datasetsProvider: CommandPaletteProvider = {
    id: "datasets",
    title: "Datasets",
    /** Datasets opened through the palette before, most recent first */
    emptyQueryItems(ctx: PaletteContext) {
        if (ctx.isAnonymous) {
            return [];
        }
        return recentItems("");
    },
    /** Root mode fan-out, filtering the cached summaries without a request */
    async search(query: string, ctx: PaletteContext) {
        const trimmed = query.trim();
        if (ctx.isAnonymous || !trimmed) {
            return [];
        }
        const found = (await matchingDatasets(trimmed, true)).map(datasetToItem);
        return rankPaletteItems(found, trimmed).slice(0, SECTION_CAP);
    },
    async searchScoped(_scope, query: string, ctx: PaletteContext) {
        if (ctx.isAnonymous) {
            return [];
        }
        const trimmed = query.trim();
        const recent = recentItems(trimmed);
        if (!trimmed) {
            const datasetListStore = useDatasetListStore();
            await ensureLatestHydrated();
            const latest = [...datasetListStore.latestDatasets].sort(byUpdateTimeDesc).map(datasetToItem);
            return toSections([
                { id: "recent", items: recent, title: localize("Recent") },
                {
                    id: "latest",
                    items: withoutItems(latest, recent).slice(0, SECTION_CAP),
                    title: localize("Latest datasets"),
                },
            ]);
        }
        const found = rankPaletteItems((await matchingDatasets(trimmed)).map(datasetToItem), trimmed);
        return toSections([
            { id: "recent", items: recent, title: localize("Recent") },
            { id: "results", items: withoutItems(found, recent).slice(0, SECTION_CAP), title: localize("Datasets") },
        ]);
    },
};
