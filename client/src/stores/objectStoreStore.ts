import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

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

    /**
     * Convenience function to add or update an object store in the list of selectable object stores without
     * reloading it from the server.
     * @param objectStore The object store to add or update
     */
    function addOrUpdateObjectStore(objectStore: ConcreteObjectStoreModel) {
        if (selectableObjectStores.value) {
            const index = selectableObjectStores.value.findIndex(
                (store) => store.object_store_id === objectStore.object_store_id
            );
            if (index !== -1) {
                set(selectableObjectStores.value, index, objectStore);
            } else {
                selectableObjectStores.value.push(objectStore);
            }
        }
    }

    loadObjectStores();

    return {
        isLoaded,
        isLoading,
        loadErrorMessage,
        selectableObjectStores,
        getObjectStoreNameById,
        addOrUpdateObjectStore,
    };
});
