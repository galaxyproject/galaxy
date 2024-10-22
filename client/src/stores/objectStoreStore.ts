import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { type ConcreteObjectStoreModel } from "@/api";
import { getSelectableObjectStores } from "@/api/objectStores";
import { errorMessageAsString } from "@/utils/simple-error";

export const useObjectStoreStore = defineStore("objectStoreStore", () => {
    const selectableObjectStores = ref<ConcreteObjectStoreModel[] | null>(null);
    const loadErrorMessage = ref<string | null>(null);
    const isLoading = ref(false);
    const isLoaded = computed(() => selectableObjectStores.value != null);

    async function loadObjectStores() {
        if (!isLoaded.value && !isLoading.value) {
            isLoading.value = true;
            try {
                const data = await getSelectableObjectStores();
                selectableObjectStores.value = data;
            } catch (err) {
                const errorMessage = `Error loading Galaxy object stores: ${errorMessageAsString(err)}`;
                loadErrorMessage.value = errorMessage;
                console.error("Error loading Galaxy object stores", err);
            } finally {
                isLoading.value = false;
            }
        }
    }

    function getObjectStoreNameById(objectStoreId: string): string | null {
        const objectStore = selectableObjectStores.value?.find((store) => store.object_store_id === objectStoreId);
        return objectStore?.name ?? null;
    }

    loadObjectStores();

    return {
        isLoaded,
        isLoading,
        loadErrorMessage,
        selectableObjectStores,
        getObjectStoreNameById,
    };
});
