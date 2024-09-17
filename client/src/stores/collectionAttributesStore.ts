import { defineStore } from "pinia";

import { type DatasetCollectionAttributes, GalaxyApi } from "@/api";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { rethrowSimple } from "@/utils/simple-error";

export const useCollectionAttributesStore = defineStore("collectionAttributesStore", () => {
    async function fetchAttributes(params: FetchParams): Promise<DatasetCollectionAttributes> {
        const { data, error } = await GalaxyApi().GET("/api/dataset_collections/{id}/attributes", {
            params: { path: params },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    const { storedItems, getItemById, isLoadingItem, hasItemLoadError } =
        useKeyedCache<DatasetCollectionAttributes>(fetchAttributes);

    return {
        storedAttributes: storedItems,
        getAttributes: getItemById,
        isLoadingAttributes: isLoadingItem,
        hasItemLoadError: hasItemLoadError,
    };
});
