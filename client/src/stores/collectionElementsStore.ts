import { defineStore } from "pinia";
import Vue, { computed, ref } from "vue";

import { CollectionEntry, DCESummary, HDCASummary, HistoryContentItemBase, isHDCA } from "./services";
import * as Service from "./services/datasetCollection.service";

/**
 * Represents a dataset collection element that has not been fetched yet.
 */
interface DCEPlaceholder extends DCESummary {
    id: "placeholder";
    fetching: boolean;
}

type DCEEntry = DCEPlaceholder | DCESummary;

const PLACEHOLDER_TEXT = "Loading...";
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
                .findIndex((element) => isPlaceholder(element) && element.fetching === false);

            if (firstMissingIndexInRange === -1) {
                // All elements in the range are already stored or being fetched
                return;
            }
            // Adjust the offset to the first missing element
            params.offset += firstMissingIndexInRange;

            Vue.set(loadingCollectionElements.value, collectionKey, true);
            // Mark all elements in the range as fetching
            params.storedElements
                .slice(params.offset, params.offset + params.limit)
                .forEach((element) => isPlaceholder(element) && (element.fetching = true));
            const fetchedElements = await Service.fetchElementsFromCollection({
                entry: params.collection,
                offset: params.offset,
                limit: params.limit,
            });
            // Update only the elements that were fetched
            params.storedElements.splice(params.offset, fetchedElements.length, ...fetchedElements);
            Vue.set(storedCollectionElements.value, collectionKey, params.storedElements);
        } finally {
            Vue.delete(loadingCollectionElements.value, collectionKey);
        }
    }

    async function loadCollectionElements(collection: CollectionEntry) {
        const elements = await Service.fetchElementsFromCollection({ entry: collection });
        Vue.set(storedCollectionElements.value, getCollectionKey(collection), elements);
    }

    function saveCollections(historyContentsPayload: HistoryContentItemBase[]) {
        const collectionsInHistory = historyContentsPayload.filter(
            (entry) => entry.history_content_type === "dataset_collection"
        ) as HDCASummary[];
        for (const collection of collectionsInHistory) {
            Vue.set<HDCASummary>(storedCollections.value, collection.id, collection);
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
        Vue.set(loadingCollectionElements.value, params.id, true);
        try {
            const collection = await Service.fetchCollectionDetails({ hdcaId: params.id });
            Vue.set(storedCollections.value, collection.id, collection);
            return collection;
        } finally {
            Vue.delete(loadingCollectionElements.value, params.id);
        }
    }

    function isPlaceholder(element: DCEEntry): element is DCEPlaceholder {
        return element.id === "placeholder";
    }

    function initWithPlaceholderElements(collection: CollectionEntry): DCEPlaceholder[] {
        const totalElements = collection.element_count ?? 0;
        const placeholderElements = new Array<DCEPlaceholder>(totalElements)
            .fill({
                id: "placeholder",
                fetching: false,
                element_identifier: PLACEHOLDER_TEXT,
                element_index: 0,
                element_type: "hda",
                model_class: "DatasetCollectionElement",
                object: {
                    id: "placeholder",
                    model_class: "HistoryDatasetAssociation",
                    state: "ok",
                    hda_ldda: "hda",
                    history_id: "1",
                    tags: [],
                },
            })
            .map((placeholder, index) => {
                return {
                    ...placeholder,
                    element_index: index,
                };
            });
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
