import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { UserConcreteObjectStoreModel } from "@/api";
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

    /** Names of the storages counting toward each quota source; one with its quota disabled counts toward none. */
    const storeNamesByQuotaSource = computed<Record<string, string[]>>(() => {
        const namesBySource: Record<string, string[]> = {};
        for (const store of selectableObjectStores.value ?? []) {
            const source = store.quota.source;
            if (source && store.quota.enabled && store.name) {
                (namesBySource[source] ??= []).push(store.name);
            }
        }
        return namesBySource;
    });

    function getObjectStoreNameById(id?: string | null) {
        if (id) {
            const store = objectStoresById.value[id];
            return store?.name ?? null;
        } else {
            return null;
        }
    }

    /**
     * Convenience function to add or update an object store in the list of selectable object stores without
     * reloading it from the server.
     * @param objectStore The object store to add or update
     */
    function addOrUpdateObjectStore(objectStore: UserConcreteObjectStoreModel) {
        if (selectableObjectStores.value) {
            const index = selectableObjectStores.value.findIndex(
                (store) => store.object_store_id === objectStore.object_store_id,
            );
            if (index !== -1) {
                selectableObjectStores.value[index] = objectStore;
            } else {
                selectableObjectStores.value.push(objectStore);
            }
        }
    }

    loadObjectStores();

    return {
        loading,
        loadErrorMessage,
        selectableObjectStores,
        storeNamesByQuotaSource,
        getObjectStoreNameById,
        addOrUpdateObjectStore,
    };
});
