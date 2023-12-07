import { defineStore } from "pinia";

import type { DatasetCollectionAttributes } from "@/api";
import { fetchCollectionAttributes } from "@/api/datasetCollections";
import { useSimpleKeyStore } from "@/composables/simpleKeyStore";

export const useCollectionAttributesStore = defineStore("collectionAttributesStore", () => {
    const { storedItems, getItemById, isLoadingItem } = useSimpleKeyStore<DatasetCollectionAttributes>((params) =>
        fetchCollectionAttributes({ id: params.id, instance_type: "history" })
    );

    return {
        storedAttributes: storedItems,
        getAttributes: getItemById,
        isLoadingAttributes: isLoadingItem,
    };
});
