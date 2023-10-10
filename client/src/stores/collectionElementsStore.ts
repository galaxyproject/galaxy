import { defineStore } from "pinia";
import Vue, { computed, ref } from "vue";

import { DCESummary, HDCASummary, HistoryContentItemBase } from "./services";
import * as Service from "./services/datasetCollection.service";

export const useCollectionElementsStore = defineStore("collectionElementsStore", () => {
    const storedCollections = ref<{ [key: string]: HDCASummary }>({});
    const loadingCollectionElements = ref<{ [key: string]: boolean }>({});
    const storedCollectionElements = ref<{ [key: string]: DCESummary[] }>({});

    /**
     * Returns a key that can be used to store or retrieve the elements of a collection in the store.
     */
    function getCollectionKey(collection: HDCASummary): string {
        return collection.collection_id;
    }

    const getCollectionElements = computed(() => {
        return (collection: HDCASummary, offset = 0, limit = 50) => {
            const elements = storedCollectionElements.value[getCollectionKey(collection)] ?? [];
            fetchMissingElements({ collection, offset, limit });
            return elements ?? null;
        };
    });

    const isLoadingCollectionElements = computed(() => {
        return (collection: HDCASummary) => {
            return loadingCollectionElements.value[getCollectionKey(collection)] ?? false;
        };
    });

    async function fetchMissingElements(params: { collection: HDCASummary; offset: number; limit: number }) {
        const collectionKey = getCollectionKey(params.collection);
        try {
            const maxElementCountInCollection = params.collection.element_count ?? 0;
            const storedElements = storedCollectionElements.value[collectionKey] ?? [];
            // Collections are immutable, so there is no need to fetch elements if the range we want is already stored
            if (params.offset + params.limit <= storedElements.length) {
                return;
            }
            // If we already have items at the offset, we can start fetching from the next offset
            params.offset = storedElements.length;

            if (params.offset >= maxElementCountInCollection) {
                return;
            }

            Vue.set(loadingCollectionElements.value, collectionKey, true);
            const fetchedElements = await Service.fetchElementsFromHDCA({
                hdca: params.collection,
                offset: params.offset,
                limit: params.limit,
            });
            const updatedElements = [...storedElements, ...fetchedElements];
            Vue.set(storedCollectionElements.value, collectionKey, updatedElements);
        } finally {
            Vue.delete(loadingCollectionElements.value, collectionKey);
        }
    }

    async function loadCollectionElements(collection: HDCASummary) {
        const elements = await Service.fetchElementsFromHDCA({ hdca: collection });
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
