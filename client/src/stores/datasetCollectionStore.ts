/**
 * Cached fetcher for `/api/dataset_collections/{hdca_id}` — owns the
 * `HDCASummary | HDCADetailed` cache. Parallels `datasetStore` for HDAs:
 * one map per id, detail upgrades summary in place.
 *
 * Element pagination — and the staleness invalidation that comes with it —
 * lives in `collectionElementsStore`. Don't read `HDCADetailed.elements`
 * for fresh element lists; that field is a snapshot at fetch time.
 */

import { defineStore } from "pinia";
import { computed, set } from "vue";

import {
    GalaxyApi,
    type HDCADetailed,
    type HDCASummary,
    type HistoryContentItemBase,
    isDetailedCollection,
} from "@/api";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { rethrowSimpleWithStatus } from "@/utils/simple-error";

type CollectionEntry = HDCASummary | HDCADetailed;

export const useDatasetCollectionStore = defineStore("datasetCollectionStore", () => {
    async function fetchCollectionDetail(params: FetchParams): Promise<HDCADetailed> {
        const { data, error, response } = await GalaxyApi().GET("/api/dataset_collections/{hdca_id}", {
            params: { path: { hdca_id: params.id } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data as HDCADetailed;
    }

    // Refetch when the cache slot is empty or holds only a summary. Once detail
    // is cached, it stays — same behaviour as the previous store. Element
    // staleness is orthogonal and handled by `collectionElementsStore`.
    const shouldFetchDetail = computed(() => {
        return (entry?: CollectionEntry) => !entry || !isDetailedCollection(entry);
    });

    const { storedItems, getItemById, getItemLoadError, isLoadingItem, fetchItemById } = useKeyedCache<CollectionEntry>(
        fetchCollectionDetail,
        shouldFetchDetail,
    );

    /**
     * Returns whatever is cached for the given id — summary or detail.
     * Triggers a fetch only if nothing is cached at all, so callers that
     * only need summary-level fields (e.g. `job_source_id`) don't force a
     * detail upgrade when a summary is already present.
     */
    function getCollection(id: string): CollectionEntry | null {
        const cached = storedItems.value[id];
        if (cached) {
            return cached;
        }
        fetchItemById({ id });
        return null;
    }

    /**
     * Returns the detailed payload for the given id, fetching (or upgrading
     * from summary) if not already detail. Matches the previous
     * `getDetailedCollectionById` behaviour. Returns `null` while loading.
     */
    const getDetailedCollection = getItemById;

    /** Single-entry write — used by the bulk save below and by callers
     *  that already have a fresh payload in hand. */
    function saveCollection(collection: CollectionEntry) {
        set(storedItems.value, collection.id, collection);
    }

    /** Bulk-update from a history-contents payload. Filters to collection
     *  entries; everything else is ignored. */
    function saveCollections(historyContentsPayload: HistoryContentItemBase[]) {
        for (const entry of historyContentsPayload) {
            if (entry.history_content_type === "dataset_collection") {
                saveCollection(entry as HDCASummary);
            }
        }
    }

    return {
        storedCollections: storedItems,
        getCollection,
        getDetailedCollection,
        getCollectionError: getItemLoadError,
        isLoadingCollection: isLoadingItem,
        fetchCollection: fetchItemById,
        saveCollection,
        saveCollections,
    };
});
