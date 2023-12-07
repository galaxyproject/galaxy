import { computed, del, ref, set } from "vue";

import type { ApiResponse } from "@/api/schema";

/**
 * Parameters for fetching an item from the server.
 *
 * Minimally, this should include an id for indexing the item.
 */
interface FetchParams {
    id: string;
}

/**
 * A function that fetches an item from the server.
 */
interface FetchFunction<T> {
    (params: FetchParams): Promise<ApiResponse<T>>;
}

/**
 * A function that returns true if the item should be fetched.
 * Provides fine-grained control over when to fetch an item.
 */
interface ShouldFetch<T> {
    (item?: T): boolean;
}

/**
 * A composable that provides a simple key-value store for items fetched from the server.
 *
 * This is useful for storing items that are fetched by id.
 *
 * @param fetchItem A function that fetches an item from the server.
 * @param shouldFetch A function that returns true if the item should be fetched.
 * Provides fine-grained control over when to fetch an item.
 * If not provided, by default, the item will be fetched if it is not already stored.
 */
export function useSimpleKeyStore<T>(fetchItem: FetchFunction<T>, shouldFetch: ShouldFetch<T> = (item) => !item) {
    const storedItems = ref<{ [key: string]: T }>({});
    const loadingItem = ref<{ [key: string]: boolean }>({});

    const getItemById = computed(() => {
        return (id: string) => {
            const item = storedItems.value[id];
            if (!loadingItem.value[id] && shouldFetch(item)) {
                fetchItemById({ id: id });
            }
            return item ?? null;
        };
    });

    const isLoadingItem = computed(() => {
        return (id: string) => {
            return loadingItem.value[id] ?? false;
        };
    });

    async function fetchItemById(params: FetchParams) {
        const itemId = params.id;
        set(loadingItem.value, itemId, true);
        try {
            const { data } = await fetchItem({ id: itemId });
            set(storedItems.value, itemId, data);
            return data;
        } finally {
            del(loadingItem.value, itemId);
        }
    }

    return {
        /**
         * The stored items as a reactive object.
         */
        storedItems,
        /**
         * A computed function that returns the item with the given id.
         * If the item is not already stored, it will be fetched from the server.
         * And reactively updated when the fetch completes.
         */
        getItemById,
        /**
         * A computed function that returns true if the item with the given id is currently being fetched.
         */
        isLoadingItem,
        /**
         * Fetches the item with the given id from the server.
         * And reactively updates the stored item when the fetch completes.
         */
        fetchItemById,
    };
}
