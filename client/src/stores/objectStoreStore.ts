import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { type ConcreteObjectStoreModel } from "@/api";
import { getSelectableObjectStores } from "@/api/objectStores";
import { errorMessageAsString } from "@/utils/simple-error";

export const useObjectStoreStore = defineStore("objectStoreStore", () => {
    const selectableObjectStores = ref<ConcreteObjectStoreModel[] | null>(null);
    const loading = ref(false);
    const loadErrorMessage = ref<string | null>(null);

    async function fetchObjectStores() {
        if (!loading.value && selectableObjectStores.value === null) {
            loading.value = true;
            try {
                loadErrorMessage.value = null;
                const data = await getSelectableObjectStores();
                selectableObjectStores.value = data;
            } catch (err) {
                const errorMessage = `Error loading Galaxy object stores: ${errorMessageAsString(err)}`;
                loadErrorMessage.value = errorMessage;
                console.error("Error loading Galaxy object stores", err);
            } finally {
                loading.value = false;
            }
        }
    }

    const objectStoresById = computed<Record<string, ConcreteObjectStoreModel>>(() => {
        const stores = selectableObjectStores.value;

        if (stores) {
            const storesWithId = stores.filter((store) => Boolean(store.object_store_id));

            return Object.fromEntries(storesWithId.map((store) => [store.object_store_id, store]));
        } else {
            return {};
        }
    });

    function getObjectStoreNameById(id?: string | null) {
        if (id) {
            const store = objectStoresById.value[id];
            return store?.name ?? id;
        } else {
            return null;
        }
    }

    return {
        selectableObjectStores,
        loading,
        loadErrorMessage,
        fetchObjectStores,
        getObjectStoreNameById,
        objectStoresById,
    };
});
