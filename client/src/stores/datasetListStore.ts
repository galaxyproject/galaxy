import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import type { HDASummary } from "@/api";
import { loadDatasets } from "@/api/datasets";
import { errorMessageAsString } from "@/utils/simple-error";

/** Number of dataset summaries fetched when hydrating the "latest" list. */
const DEFAULT_LIMIT = 25;

export interface FetchDatasetsOptions {
    /** Free text matched against the dataset name (server-side `name-contains`). */
    search?: string;
    /** Maximum number of datasets to request. */
    limit?: number;
}

/**
 * Caches dataset *summaries* (`HDASummary`) for list-like consumers such as the
 * command palette. Detailed datasets (`HDADetailed`) keep living in
 * `datasetStore`; this store only holds the lightweight list representation and
 * the ordering of the most recently updated datasets.
 */
export const useDatasetListStore = defineStore("datasetListStore", () => {
    const storedDatasets = ref<Record<string, HDASummary>>({});
    /** Dataset ids ordered by `update_time` descending, as returned by the API. */
    const latestDatasetIds = ref<string[]>([]);
    const isLoading = ref(false);
    const loadError = ref<string | undefined>(undefined);
    /** Whether the unfiltered "latest" list has been fetched at least once. */
    const hasLoadedLatest = ref(false);
    /** Total number of datasets matching the last unfiltered fetch. */
    const totalLatestMatches = ref(0);

    const latestDatasets = computed<HDASummary[]>(() =>
        latestDatasetIds.value
            .map((id) => storedDatasets.value[id])
            .filter((dataset): dataset is HDASummary => Boolean(dataset)),
    );

    /** Getter, not an action: reading the cache never touches the backend. */
    const getDatasetSummary = computed(
        () =>
            (id: string): HDASummary | undefined =>
                storedDatasets.value[id],
    );

    /** Merges dataset summaries into the cache, keyed (and deduped) by id. */
    function saveDatasets(datasets: HDASummary[]) {
        for (const dataset of datasets) {
            if (!dataset?.id) {
                continue;
            }
            set(storedDatasets.value, dataset.id, dataset);
        }
    }

    /**
     * Fetches dataset summaries and merges them into the cache. Unfiltered
     * fetches also (re)define the ordered "latest" list.
     */
    async function fetchDatasets(options: FetchDatasetsOptions = {}): Promise<HDASummary[]> {
        const { search = "", limit = DEFAULT_LIMIT } = options;
        isLoading.value = true;
        loadError.value = undefined;
        try {
            const { data, totalMatches } = await loadDatasets({
                sortBy: "update_time",
                sortDesc: true,
                limit,
                search,
            });
            saveDatasets(data);
            if (!search) {
                latestDatasetIds.value = dedupeIds(data.map((dataset) => dataset.id));
                totalLatestMatches.value = totalMatches;
                hasLoadedLatest.value = true;
            }
            return data;
        } catch (error) {
            loadError.value = errorMessageAsString(error);
            return [];
        } finally {
            isLoading.value = false;
        }
    }

    /** Fetches the latest datasets once; later calls resolve from the cache. */
    async function ensureLatestLoaded(limit = DEFAULT_LIMIT): Promise<HDASummary[]> {
        if (hasLoadedLatest.value) {
            return latestDatasets.value;
        }
        await fetchDatasets({ limit });
        return latestDatasets.value;
    }

    /**
     * Client-side name filter over everything currently cached. A getter rather
     * than an action, so consumers that must not hit the backend (the command
     * palette's unscoped fan-out) cannot accidentally trigger a request.
     */
    const searchCachedDatasets = computed(() => (query: string, limit = DEFAULT_LIMIT): HDASummary[] => {
        const term = query.trim().toLowerCase();
        const cached = Object.values(storedDatasets.value);
        const matches = term ? cached.filter((dataset) => dataset.name?.toLowerCase().includes(term)) : cached;
        return matches.slice(0, limit);
    });

    return {
        storedDatasets,
        latestDatasetIds,
        latestDatasets,
        isLoading,
        loadError,
        hasLoadedLatest,
        totalLatestMatches,
        getDatasetSummary,
        saveDatasets,
        fetchDatasets,
        ensureLatestLoaded,
        searchCachedDatasets,
    };
});

function dedupeIds(ids: string[]): string[] {
    return Array.from(new Set(ids));
}
