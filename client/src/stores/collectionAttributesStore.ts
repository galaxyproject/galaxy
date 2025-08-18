import { defineStore } from "pinia";

import { type DatasetCollectionAttributes, GalaxyApi } from "@/api";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { rethrowSimple } from "@/utils/simple-error";

export const useCollectionAttributesStore = defineStore("collectionAttributesStore", () => {
    async function fetchAttributes(params: FetchParams): Promise<DatasetCollectionAttributes> {
        const { data, error } = await GalaxyApi().GET("/api/dataset_collections/{hdca_id}/attributes", {
            params: { path: { hdca_id: params.id } },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    const { storedItems, getItemById, isLoadingItem, getItemLoadError } =
        useKeyedCache<DatasetCollectionAttributes>(fetchAttributes);

    return {
        storedAttributes: storedItems,
        getAttributes: getItemById,
        isLoadingAttributes: isLoadingItem,
        getItemLoadError: getItemLoadError,
    };
});
