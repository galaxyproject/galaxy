import { defineStore } from "pinia";
import { computed, del, ref, set } from "vue";

import type { CollectionEntry, DCESummary, HDCASummary, HistoryContentItemBase } from "@/api";
import { isHDCA } from "@/api";
import { fetchCollectionDetails, fetchElementsFromCollection } from "@/api/datasetCollections";
import { ensureDefined } from "@/utils/assertions";
import { ActionSkippedError, LastQueue } from "@/utils/lastQueue";

/**
 * Represents an element in a collection that has not been fetched yet.
 */
export interface ContentPlaceholder {
    /**
     * The index of the element in the containing collection.
     *
     * This is used to determine the offset to fetch the element from when
     * scrolling through the collection.
     */
    element_index: number;
    /**
     * Whether the element is currently being fetched.
     *
     * This is used to prevent fetching the same element multiple times.
     */
    fetching?: boolean;
}

export type InvalidDCEEntry = (ContentPlaceholder | DCESummary) & {
    valid: false;
};

export type DCEEntry = ContentPlaceholder | DCESummary | InvalidDCEEntry;

const FETCH_LIMIT = 50;

export const useCollectionElementsStore = defineStore("collectionElementsStore", () => {
    const storedCollections = ref<{ [key: string]: HDCASummary }>({});
    const loadingCollectionElements = ref<{ [key: string]: boolean }>({});
    const loadingCollectionElementsErrors = ref<{ [key: string]: Error }>({});
    const storedCollectionElements = ref<{ [key: string]: DCEEntry[] }>({});

    /**
     * Returns a key that can be used to store or retrieve the elements of a collection in the store.
     *
     * It consistently returns a DatasetCollection ID for (top level) HDCAs or sub-collections.
     */
    function getCollectionKey(collection: CollectionEntry): string {
        if (isHDCA(collection)) {
            return collection.collection_id;
        }
        return collection.id;
    }

    const getCollectionElements = computed(() => {
        return (collection: CollectionEntry) => {
            return storedCollectionElements.value[getCollectionKey(collection)];
        };
    });

    const isLoadingCollectionElements = computed(() => {
        return (collection: CollectionEntry) => {
            return loadingCollectionElements.value[getCollectionKey(collection)] ?? false;
        };
    });

    const hasLoadingCollectionElementsError = computed(() => {
        return (collection: CollectionEntry) => {
            return loadingCollectionElementsErrors.value[getCollectionKey(collection)] ?? false;
        };
    });

    type FetchParams = {
        storedElements: DCEEntry[];
        collection: CollectionEntry;
        offset: number;
        limit: number;
    };

    async function fetchMissing({ storedElements, collection, offset, limit = FETCH_LIMIT }: FetchParams) {
        const collectionKey = getCollectionKey(collection);

        try {
            if (collection.element_count !== null) {
                // We should fetch only missing (placeholder) elements from the range
                const firstMissingIndexInRange = storedElements
                    .slice(offset, offset + limit)
                    .findIndex((element) => (isPlaceholder(element) && !element.fetching) || isInvalid(element));

                if (firstMissingIndexInRange === -1) {
                    // All elements in the range are already stored or being fetched
                    return;
                }

                // Adjust the offset to the first missing element
                offset += firstMissingIndexInRange;
            } else {
                // Edge case where element_count is incorrect
                // TODO: remove me once element_count is reported reliably
                offset = 0;
            }

            set(loadingCollectionElements.value, collectionKey, true);
            // Mark all elements in the range as fetching
            storedElements
                .slice(offset, offset + limit)
                .forEach((element) => isPlaceholder(element) && (element.fetching = true));

            const fetchedElements = await fetchElementsFromCollection({
                entry: collection,
                offset: offset,
                limit: limit,
            });

            return { fetchedElements, elementOffset: offset };
        } catch (error) {
            set(loadingCollectionElementsErrors.value, collectionKey, error);
        } finally {
            del(loadingCollectionElements.value, collectionKey);
        }
    }

    const lastQueue = new LastQueue<typeof fetchMissing>(1000, true);

    async function fetchMissingElements(collection: CollectionEntry, offset: number, limit = FETCH_LIMIT) {
        const key = getCollectionKey(collection);
        let storedElements = storedCollectionElements.value[key];

        if (!storedElements) {
            storedElements = initWithPlaceholderElements(collection);
            set(storedCollectionElements.value, key, storedElements);
        }

        try {
            const data = await lastQueue.enqueue(fetchMissing, { storedElements, collection, offset, limit }, key);

            if (data) {
                const from = data.elementOffset;
                const to = from + data.fetchedElements.length;

                for (let index = from; index < to; index++) {
                    const element = ensureDefined(data.fetchedElements[index - from]);
                    set(storedElements, index, element);
                }

                set(storedCollectionElements.value, key, storedElements);
            }
        } catch (e) {
            if (!(e instanceof ActionSkippedError)) {
                throw e;
            }
        }
    }

    async function invalidateCollectionElements(collection: CollectionEntry) {
        const storedElements = storedCollectionElements.value[getCollectionKey(collection)] ?? [];
        storedElements.forEach((element) => {
            (element as InvalidDCEEntry).valid = false;
        });
    }

    function saveCollections(historyContentsPayload: HistoryContentItemBase[]) {
        const collectionsInHistory = historyContentsPayload.filter(
            (entry) => entry.history_content_type === "dataset_collection"
        ) as HDCASummary[];
        for (const collection of collectionsInHistory) {
            set<HDCASummary>(storedCollections.value, collection.id, collection);
        }
    }

    /** Returns collection from storedCollections, will load collection if not in store */
    const getCollectionById = computed(() => {
        return (collectionId: string) => {
            if (!storedCollections.value[collectionId] && !loadingCollectionElementsErrors.value[collectionId]) {
                // TODO: Try to remove this as it can cause computed side effects (use keyedCache in this store instead?)
                fetchCollection({ id: collectionId });
            }
            return storedCollections.value[collectionId] ?? null;
        };
    });

    async function fetchCollection(params: { id: string }) {
        set(loadingCollectionElements.value, params.id, true);
        try {
            const collection = await fetchCollectionDetails({ id: params.id });
            set(storedCollections.value, collection.id, collection);
            return collection;
        } catch (error) {
            set(loadingCollectionElementsErrors.value, params.id, error);
        } finally {
            del(loadingCollectionElements.value, params.id);
        }
    }

    function isPlaceholder(element: DCEEntry): element is ContentPlaceholder {
        return "id" in element === false;
    }

    function isInvalid(element: DCEEntry): element is InvalidDCEEntry {
        return (element as InvalidDCEEntry)["valid"] === false;
    }

    function initWithPlaceholderElements(collection: CollectionEntry): ContentPlaceholder[] {
        const totalElements = collection.element_count ?? 0;
        const placeholderElements = new Array<ContentPlaceholder>(totalElements);
        for (let i = 0; i < totalElements; i++) {
            placeholderElements[i] = { element_index: i };
        }
        return placeholderElements;
    }

    return {
        storedCollections,
        storedCollectionElements,
        getCollectionElements,
        isLoadingCollectionElements,
        hasLoadingCollectionElementsError,
        loadingCollectionElementsErrors,
        getCollectionById,
        fetchCollection,
        invalidateCollectionElements,
        saveCollections,
        getCollectionKey,
        fetchMissingElements,
    };
});
