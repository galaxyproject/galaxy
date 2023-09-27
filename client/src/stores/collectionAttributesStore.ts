import { defineStore } from "pinia";
import Vue, { computed, ref } from "vue";

import { DatasetCollectionAttributes } from "./services";
import * as Service from "./services/datasetCollection.service";

export const useCollectionAttributesStore = defineStore("collectionAttributesStore", () => {
    const storedAttributes = ref<{ [key: string]: DatasetCollectionAttributes }>({});
    const loadingAttributes = ref<{ [key: string]: boolean }>({});

    const getAttributes = computed(() => {
        return (hdcaId: string) => {
            if (!storedAttributes.value[hdcaId]) {
                Vue.set(storedAttributes.value, hdcaId, {});
                fetchAttributes({ hdcaId });
            }
            return storedAttributes.value[hdcaId];
        };
    });

    const isLoadingAttributes = computed(() => {
        return (hdcaId: string) => {
            return loadingAttributes.value[hdcaId] ?? false;
        };
    });

    async function fetchAttributes(params: { hdcaId: string }) {
        Vue.set(loadingAttributes.value, params.hdcaId, true);
        try {
            const attributes = await Service.fetchCollectionAttributes(params);
            Vue.set(storedAttributes.value, params.hdcaId, attributes);
            return attributes;
        } finally {
            Vue.delete(loadingAttributes.value, params.hdcaId);
        }
    }

    return {
        storedAttributes,
        getAttributes,
        isLoadingAttributes,
    };
});
