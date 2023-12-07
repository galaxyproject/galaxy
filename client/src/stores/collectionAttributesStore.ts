import { defineStore } from "pinia";

import type { DatasetCollectionAttributes } from "@/api";
import { fetchCollectionAttributes } from "@/api/datasetCollections";
import { useSimpleStore } from "@/composables/simpleStore";

export const useCollectionAttributesStore = defineStore("collectionAttributesStore", () => {
    const { storedItems, getItemById, isLoadingItem } = useSimpleStore<DatasetCollectionAttributes>((params) =>
        fetchCollectionAttributes({ id: params.id, instance_type: "history" })
    );

    return {
        storedAttributes: storedItems,
        getAttributes: getItemById,
        isLoadingAttributes: isLoadingItem,
    };
});
