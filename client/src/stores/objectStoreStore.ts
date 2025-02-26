import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { type UserConcreteObjectStoreModel } from "@/api";
import { getSelectableObjectStores } from "@/api/objectStores";
import { errorMessageAsString } from "@/utils/simple-error";

export const useObjectStoreStore = defineStore("objectStoreStore", () => {
    const selectableObjectStores = ref<UserConcreteObjectStoreModel[] | null>(null);
    const loadErrorMessage = ref<string | null>(null);
    const loading = ref(false);

    async function loadObjectStores() {
        if (!loading.value && selectableObjectStores.value === null) {
            loading.value = true;

            try {
                loadErrorMessage.value = null;
                const data = await getSelectableObjectStores();
                selectableObjectStores.value = data as UserConcreteObjectStoreModel[];
            } catch (err) {
                const errorMessage = `Error loading Galaxy object stores: ${errorMessageAsString(err)}`;
                loadErrorMessage.value = errorMessage;
                console.error("Error loading Galaxy object stores", err);
            } finally {
                loading.value = false;
            }
        }
    }

    const objectStoresById = computed<Record<string, UserConcreteObjectStoreModel>>(() => {
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
            return store?.name ?? null;
        } else {
            return null;
        }
    }

    loadObjectStores();

    return {
        loading,
        loadErrorMessage,
        selectableObjectStores,
        getObjectStoreNameById,
    };
});
