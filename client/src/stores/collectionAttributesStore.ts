import { defineStore } from "pinia";

import { client, type DatasetCollectionAttributes } from "@/api";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { rethrowSimple } from "@/utils/simple-error";

export const useCollectionAttributesStore = defineStore("collectionAttributesStore", () => {
    async function fetchAttributes(params: FetchParams): Promise<DatasetCollectionAttributes> {
        const { data, error } = await client.GET("/api/dataset_collections/{id}/attributes", {
            params: { path: params },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    const { storedItems, getItemById, isLoadingItem } = useKeyedCache<DatasetCollectionAttributes>(fetchAttributes);

    return {
        storedAttributes: storedItems,
        getAttributes: getItemById,
        isLoadingAttributes: isLoadingItem,
    };
});
