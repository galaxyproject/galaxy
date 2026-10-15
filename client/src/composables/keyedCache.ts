import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { computed, del, type Ref, ref, set, unref } from "vue";

import { useRetryGate } from "@/composables/retryGate";
import { LastQueue } from "@/utils/lastQueue";

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
type FetchHandler<T> = (params: FetchParams, signal?: AbortSignal) => Promise<T>;

/**
 * A function that returns true if the item should be fetched.
 * Provides fine-grained control over when to fetch an item.
 */
type ShouldFetchHandler<T> = (item?: T) => boolean;

/**
 * Returns true if the item is not defined.
 * @param item The item to check.
 */
const fetchIfAbsent = <T>(item?: T) => item === undefined;

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
    shouldFetchHandler?: MaybeRefOrGetter<ShouldFetchHandler<T>>,
) {
    const storedItems = ref<{ [key: string]: T }>({});
    const loadingErrors = ref<{ [key: string]: Error }>({});

    const loadingRequests = ref<{ [key: string]: Promise<T | undefined> }>({});

    const retryGate = useRetryGate();

    const fetchQueue = new LastQueue<FetchHandler<T>>();

    const getItemById = computed(() => {
        return (id: string) => {
            const item = storedItems.value[id];
            const existingError = loadingErrors.value[id];
            if (shouldFetch(item) && (!existingError || retryGate.canRetry(id, existingError))) {
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
            // A pending retry counts as loading, so consumers show progress during backoff.
            return Boolean(loadingRequests.value[id]) || retryGate.isRetryPending(id);
        };
    });

    const getItemLoadError = computed(() => {
        return (id: string) => retryGate.finalError(id, loadingErrors.value[id]);
    });

    async function fetchItemById(params: FetchParams): Promise<T | undefined> {
        const itemId = params.id;

        if (loadingRequests.value[itemId]) {
            return loadingRequests.value[itemId];
        }

        const fetchPromise = (async () => {
            try {
                const fetchItem = unref(fetchItemHandler);
                const item = await fetchQueue.enqueue(fetchItem, { id: itemId }, itemId);
                set(storedItems.value, itemId, item);
                del(loadingErrors.value, itemId);
                retryGate.recordSuccess(itemId);
                return item;
            } catch (error) {
                // A 429 here already went through the GalaxyApi rate-limiter middleware's own retries.
                retryGate.recordFailure(itemId, error as Error);
                set(loadingErrors.value, itemId, error as Error);
            } finally {
                del(loadingRequests.value, itemId);
            }
        })();

        set(loadingRequests.value, itemId, fetchPromise);
        return fetchPromise;
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
         * A computed function returning the load error for an id; null while a retry is pending or in flight.
         */
        getItemLoadError,
        /**
         * A computed function that returns true if the item with the given id is being fetched or waiting to retry.
         */
        isLoadingItem,
        /**
         * Fetches the item with the given id from the server.
         * And reactively updates the stored item when the fetch completes.
         */
        fetchItemById,
    };
}
