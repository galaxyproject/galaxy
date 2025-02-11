import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { computed, del, type Ref, ref, set, unref } from "vue";

/**
 * Parameters for fetching an item from the server.
 *
 * Minimally, this should include an id for indexing the item.
 */
export interface FetchParams {
    id: string;
}

/**
 * A function that fetches an item from the server.
 */
type FetchHandler<T> = (params: FetchParams) => Promise<T>;

/**
 * A function that returns true if the item should be fetched.
 * Provides fine-grained control over when to fetch an item.
 */
type ShouldFetchHandler<T> = (item?: T) => boolean;

/**
 * Returns true if the item is not defined.
 * @param item The item to check.
 */
const fetchIfAbsent = <T>(item?: T) => !item;

/**
 * A composable that provides a simple key-value cache for items fetched from the server.
 *
 * Useful for storing items that are fetched by id.
 *
 * @param fetchItemHandler Fetches an item from the server.
 * @param shouldFetchHandler Returns true if the item should be fetched.
 * Provides fine-grained control over when to fetch an item.
 * If not provided, by default, the item will be fetched if it is not already stored.
 */
export function useKeyedCache<T>(
    fetchItemHandler: Ref<FetchHandler<T>> | FetchHandler<T>,
    shouldFetchHandler?: MaybeRefOrGetter<ShouldFetchHandler<T>>
) {
    const storedItems = ref<{ [key: string]: T }>({});
    const loadingItem = ref<{ [key: string]: boolean }>({});
    const loadingErrors = ref<{ [key: string]: Error }>({});

    const getItemById = computed(() => {
        return (id: string) => {
            const item = storedItems.value[id];
            if (shouldFetch(item)) {
                fetchItemById({ id: id });
            }
            return item ?? null;
        };
    });

    function shouldFetch(item?: T) {
        if (shouldFetchHandler == undefined) {
            return fetchIfAbsent(item);
        }
        return toValue(shouldFetchHandler)(item);
    }

    const isLoadingItem = computed(() => {
        return (id: string) => {
            return loadingItem.value[id] ?? false;
        };
    });

    const getItemLoadError = computed(() => {
        return (id: string) => {
            return loadingErrors.value[id] ?? null;
        };
    });

    async function fetchItemById(params: FetchParams) {
        const itemId = params.id;
        const isAlreadyLoading = loadingItem.value[itemId] ?? false;
        const failedLoading = loadingErrors.value[itemId];
        if (isAlreadyLoading || failedLoading) {
            return;
        }
        set(loadingItem.value, itemId, true);
        try {
            const fetchItem = unref(fetchItemHandler);
            const item = await fetchItem({ id: itemId });
            set(storedItems.value, itemId, item);
            return item;
        } catch (error) {
            set(loadingErrors.value, itemId, error);
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
         * A computed function holding errors
         */
        getItemLoadError,
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
