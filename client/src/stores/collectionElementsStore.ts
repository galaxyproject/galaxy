import { defineStore } from "pinia";
import { computed, del, ref, set } from "vue";

import type { CollectionEntry, DCESummary, HDCASummary, HistoryContentItemBase } from "@/api";
import { isHDCA } from "@/api";
import { fetchCollectionDetails, fetchElementsFromCollection } from "@/api/datasetCollections";

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

export type DCEEntry = ContentPlaceholder | DCESummary;

const FETCH_LIMIT = 50;

export const useCollectionElementsStore = defineStore("collectionElementsStore", () => {
    const storedCollections = ref<{ [key: string]: HDCASummary }>({});
    const loadingCollectionElements = ref<{ [key: string]: boolean }>({});
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
        return (collection: CollectionEntry, offset = 0, limit = FETCH_LIMIT) => {
            const storedElements =
                storedCollectionElements.value[getCollectionKey(collection)] ?? initWithPlaceholderElements(collection);
            fetchMissingElements({ collection, storedElements, offset, limit });
            return storedElements;
        };
    });

    const isLoadingCollectionElements = computed(() => {
        return (collection: CollectionEntry) => {
            return loadingCollectionElements.value[getCollectionKey(collection)] ?? false;
        };
    });

    async function fetchMissingElements(params: {
        collection: CollectionEntry;
        storedElements: DCEEntry[];
        offset: number;
        limit: number;
    }) {
        const collectionKey = getCollectionKey(params.collection);
        try {
            // We should fetch only missing (placeholder) elements from the range
            const firstMissingIndexInRange = params.storedElements
                .slice(params.offset, params.offset + params.limit)
                .findIndex((element) => isPlaceholder(element) && !element.fetching);

            if (firstMissingIndexInRange === -1) {
                // All elements in the range are already stored or being fetched
                return;
            }
            // Adjust the offset to the first missing element
            params.offset += firstMissingIndexInRange;

            set(loadingCollectionElements.value, collectionKey, true);
            // Mark all elements in the range as fetching
            params.storedElements
                .slice(params.offset, params.offset + params.limit)
                .forEach((element) => isPlaceholder(element) && (element.fetching = true));
            const fetchedElements = await fetchElementsFromCollection({
                entry: params.collection,
                offset: params.offset,
                limit: params.limit,
            });
            // Update only the elements that were fetched
            params.storedElements.splice(params.offset, fetchedElements.length, ...fetchedElements);
            set(storedCollectionElements.value, collectionKey, params.storedElements);
        } finally {
            del(loadingCollectionElements.value, collectionKey);
        }
    }

    async function loadCollectionElements(collection: CollectionEntry) {
        const elements = await fetchElementsFromCollection({ entry: collection });
        set(storedCollectionElements.value, getCollectionKey(collection), elements);
    }

    function saveCollections(historyContentsPayload: HistoryContentItemBase[]) {
        const collectionsInHistory = historyContentsPayload.filter(
            (entry) => entry.history_content_type === "dataset_collection"
        ) as HDCASummary[];
        for (const collection of collectionsInHistory) {
            set<HDCASummary>(storedCollections.value, collection.id, collection);
        }
    }

    async function getCollection(collectionId: string) {
        const collection = storedCollections.value[collectionId];
        if (!collection) {
            return await fetchCollection({ id: collectionId });
        }
        return collection;
    }

    async function fetchCollection(params: { id: string }) {
        set(loadingCollectionElements.value, params.id, true);
        try {
            const collection = await fetchCollectionDetails({ id: params.id });
            set(storedCollections.value, collection.id, collection);
            return collection;
        } finally {
            del(loadingCollectionElements.value, params.id);
        }
    }

    function isPlaceholder(element: DCEEntry): element is ContentPlaceholder {
        return "id" in element === false;
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
        getCollection,
        fetchCollection,
        loadCollectionElements,
        saveCollections,
        getCollectionKey,
    };
});
