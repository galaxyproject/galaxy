import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, ref, watchEffect } from "vue";

import { ApiError, MAX_RETRIES } from "@/utils/simple-error";

import { type FetchParams, useKeyedCache } from "./keyedCache";

const RETRY_BACKOFF_BASE_MS = 2000;
const RETRY_BACKOFF_CAP_MS = 30_000;

interface ItemData {
    id: string;
    name: string;
}

let fetchItem = vi.fn<(params: FetchParams, signal?: AbortSignal) => Promise<ItemData>>();
let shouldFetch = vi.fn<(item?: ItemData) => boolean>();

describe("useKeyedCache", () => {
    beforeEach(() => {
        fetchItem = vi.fn<(params: FetchParams, signal?: AbortSignal) => Promise<ItemData>>();
        shouldFetch = vi.fn<(item?: ItemData) => boolean>();
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
    });

    /** Lets any scheduled retry backoff elapse. */
    async function waitOutBackoff() {
        await vi.advanceTimersByTimeAsync(RETRY_BACKOFF_CAP_MS);
    }

    it("fetches an absent item and tracks its loading state", async () => {
        const id = "1";
        const item = { id, name: "Item 1" };
        const fetchParams = { id };

        fetchItem.mockResolvedValue(item);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);

        expect(storedItems.value).toEqual({});
        expect(isLoadingItem.value(id)).toBe(false);

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBe(true);
        await flushPromises();
        expect(isLoadingItem.value(id)).toBe(false);
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
    });

    it("returns a cached item without fetching it", () => {
        const id = "1";
        const item = { id, name: "Item 1" };

        fetchItem.mockResolvedValue(item);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);

        storedItems.value[id] = item;

        expect(isLoadingItem.value(id)).toBe(false);

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBe(false);
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).not.toHaveBeenCalled();
    });

    it("treats cached zero as present", () => {
        const id = "1";
        const item = 0;
        const fetchItem = vi.fn<(params: FetchParams, signal?: AbortSignal) => Promise<number>>();
        fetchItem.mockResolvedValue(item);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<number>(fetchItem);

        storedItems.value[id] = item;

        expect(isLoadingItem.value(id)).toBe(false);

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBe(false);
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).not.toHaveBeenCalled();
    });

    it("refreshes a cached item when shouldFetch returns true", async () => {
        const id = "1";
        const item = { id, name: "Item 1" };
        const fetchParams = { id };

        fetchItem.mockResolvedValue(item);
        shouldFetch.mockReturnValue(true);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem, () => shouldFetch);

        storedItems.value[id] = item;

        expect(isLoadingItem.value(id)).toBe(false);

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBe(true);
        await flushPromises();
        expect(isLoadingItem.value(id)).toBe(false);
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
        expect(shouldFetch).toHaveBeenCalled();
    });

    it("shares one in-flight request between repeated reads", async () => {
        const id = "1";
        const item = { id, name: "Item 1" };
        const fetchParams = { id };

        fetchItem.mockResolvedValue(item);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);

        expect(isLoadingItem.value(id)).toBe(false);

        getItemById.value(id);
        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBe(true);
        await flushPromises();
        expect(isLoadingItem.value(id)).toBe(false);
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledTimes(1);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
    });

    it("shares one in-flight request even when shouldFetch returns true", async () => {
        const id = "1";
        const item = { id, name: "Item 1" };
        const fetchParams = { id };

        fetchItem.mockResolvedValue(item);
        shouldFetch.mockReturnValue(true);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem, () => shouldFetch);

        expect(isLoadingItem.value(id)).toBe(false);

        getItemById.value(id);
        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBe(true);
        await flushPromises();
        expect(isLoadingItem.value(id)).toBe(false);
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledTimes(1);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
        expect(shouldFetch).toHaveBeenCalled();
    });

    it("accepts the fetch handler as a ref", async () => {
        const id = "1";
        const item = { id, name: "Item 1" };
        const fetchParams = { id };

        fetchItem.mockResolvedValue(item);

        const fetchItemRef = ref(fetchItem);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItemRef);

        expect(isLoadingItem.value(id)).toBe(false);

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBe(true);
        await flushPromises();
        expect(isLoadingItem.value(id)).toBe(false);
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
    });

    it("accepts shouldFetch as a computed value", async () => {
        const id = "1";
        const item = { id, name: "Item 1" };
        const fetchParams = { id };

        fetchItem.mockResolvedValue(item);
        shouldFetch.mockReturnValue(true);

        const shouldFetchComputed = computed(() => shouldFetch);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem, shouldFetchComputed);

        expect(isLoadingItem.value(id)).toBe(false);

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBe(true);
        await flushPromises();
        expect(isLoadingItem.value(id)).toBe(false);
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
        expect(shouldFetch).toHaveBeenCalled();
    });

    it("does not retry an ordinary request error", async () => {
        const id = "1";

        fetchItem.mockRejectedValue(new Error("Request failed"));

        const { getItemById, getItemLoadError, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);

        getItemById.value(id);
        await flushPromises();

        expect(isLoadingItem.value(id)).toBe(false);
        expect(getItemLoadError.value(id)).toBeInstanceOf(Error);
        expect(fetchItem).toHaveBeenCalledTimes(1);

        // Calling getItemById again should not trigger another fetch
        getItemById.value(id);
        await flushPromises();

        expect(fetchItem).toHaveBeenCalledTimes(1);
    });

    it("retries a 429 response three times before stopping", async () => {
        vi.useFakeTimers();
        const id = "1";

        fetchItem.mockRejectedValue(new ApiError("Too Many Requests", 429));

        const { getItemById, getItemLoadError } = useKeyedCache<ItemData>(fetchItem);

        // Initial fetch + MAX_RETRIES retries = 4 total calls
        for (let i = 1; i <= 4; i++) {
            await waitOutBackoff();
            getItemById.value(id);
            await flushPromises();
            expect(fetchItem).toHaveBeenCalledTimes(i);
            if (i <= MAX_RETRIES) {
                // Hidden while a retry is pending.
                expect(getItemLoadError.value(id)).toBeNull();
            } else {
                expect(getItemLoadError.value(id)).toBeInstanceOf(ApiError);
            }
        }

        // Should stop after max retries exhausted
        await waitOutBackoff();
        getItemById.value(id);
        await flushPromises();
        expect(fetchItem).toHaveBeenCalledTimes(4);
    });

    it("does not retry a permanent 403 response", async () => {
        const id = "1";

        fetchItem.mockRejectedValue(new ApiError("Forbidden", 403));

        const { getItemById, getItemLoadError } = useKeyedCache<ItemData>(fetchItem);

        getItemById.value(id);
        await flushPromises();
        expect(fetchItem).toHaveBeenCalledTimes(1);
        expect(getItemLoadError.value(id)).toBeInstanceOf(ApiError);

        getItemById.value(id);
        await flushPromises();
        expect(fetchItem).toHaveBeenCalledTimes(1);
    });

    it("stores the recovered item after retrying a 503 response", async () => {
        vi.useFakeTimers();
        const id = "1";
        const item = { id, name: "Item 1" };

        fetchItem.mockRejectedValueOnce(new ApiError("Service Unavailable", 503)).mockResolvedValueOnce(item);

        const { getItemById, storedItems, getItemLoadError } = useKeyedCache<ItemData>(fetchItem);

        getItemById.value(id);
        await flushPromises();
        expect(fetchItem).toHaveBeenCalledTimes(1);
        // Hidden while a retry is pending.
        expect(getItemLoadError.value(id)).toBeNull();

        // Retry should succeed
        await waitOutBackoff();
        getItemById.value(id);
        await flushPromises();
        expect(fetchItem).toHaveBeenCalledTimes(2);
        expect(storedItems.value[id]).toEqual(item);
    });

    it("settles one delayed fetch for repeated reads when timers advance", async () => {
        vi.useFakeTimers();
        const id = "1";
        const item = { id, name: "Item 1" };
        fetchItem.mockImplementation(() => {
            return new Promise((resolve) => {
                setTimeout(() => resolve(item), 10);
            });
        });
        const { getItemById, storedItems, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);
        getItemById.value(id);
        getItemById.value(id);
        getItemById.value(id);
        expect(isLoadingItem.value(id)).toBe(true);
        expect(fetchItem).toHaveBeenCalledTimes(1);
        expect(storedItems.value[id]).toBeUndefined();

        await flushPromises();
        await vi.runOnlyPendingTimersAsync();
        await flushPromises();

        expect(isLoadingItem.value(id)).toBe(false);
        expect(fetchItem).toHaveBeenCalledTimes(1);
        expect(storedItems.value[id]).toEqual(item);
    });

    it("clears the previous error after a successful retry", async () => {
        vi.useFakeTimers();
        const id = "1";
        const item = { id, name: "Item 1" };
        fetchItem.mockRejectedValueOnce(new ApiError("service unavailable", 503));
        fetchItem.mockResolvedValue(item);

        const { getItemById, storedItems, getItemLoadError } = useKeyedCache<ItemData>(fetchItem);

        getItemById.value(id);
        await flushPromises();
        // Hidden while a retry is pending.
        expect(getItemLoadError.value(id)).toBeNull();

        await waitOutBackoff();
        getItemById.value(id);
        await flushPromises();
        expect(storedItems.value[id]).toEqual(item);
        expect(getItemLoadError.value(id)).toBeNull();
    });

    it("should clear a final error on a later successful fetch", async () => {
        vi.useFakeTimers();
        const id = "1";
        const item = { id, name: "Item 1" };
        fetchItem.mockRejectedValue(new ApiError("service unavailable", 503));

        const { fetchItemById, storedItems, getItemLoadError } = useKeyedCache<ItemData>(fetchItem);

        for (let i = 0; i <= MAX_RETRIES; i++) {
            await fetchItemById({ id });
        }
        expect(getItemLoadError.value(id)).toBeInstanceOf(ApiError);

        fetchItem.mockResolvedValue(item);
        await fetchItemById({ id });
        expect(storedItems.value[id]).toEqual(item);
        expect(getItemLoadError.value(id)).toBeNull();
    });

    describe("retry backoff", () => {
        beforeEach(() => {
            vi.useFakeTimers();
            // Lowest jitter: delay for attempt n is RETRY_BACKOFF_BASE_MS * 2^(n-1) / 2.
            vi.spyOn(Math, "random").mockReturnValue(0);
        });

        afterEach(() => {
            vi.restoreAllMocks();
        });

        function minDelay(attempt: number) {
            return (RETRY_BACKOFF_BASE_MS * 2 ** (attempt - 1)) / 2;
        }

        it("should not refetch immediately on re-evaluation after a 429", async () => {
            const id = "1";
            fetchItem.mockRejectedValue(new ApiError("Too Many Requests", 429));

            const { getItemById } = useKeyedCache<ItemData>(fetchItem);

            getItemById.value(id);
            await flushPromises();
            expect(fetchItem).toHaveBeenCalledTimes(1);

            getItemById.value(id);
            getItemById.value(id);
            await flushPromises();
            expect(fetchItem).toHaveBeenCalledTimes(1);
        });

        it("should refetch reactively once the backoff elapses, without manual re-evaluation", async () => {
            const id = "1";
            fetchItem.mockRejectedValue(new ApiError("Too Many Requests", 429));

            const { getItemById } = useKeyedCache<ItemData>(fetchItem);
            const stop = watchEffect(() => {
                getItemById.value(id);
            });
            await flushPromises();
            expect(fetchItem).toHaveBeenCalledTimes(1);

            await vi.advanceTimersByTimeAsync(minDelay(1) - 1);
            await flushPromises();
            expect(fetchItem).toHaveBeenCalledTimes(1);

            await vi.advanceTimersByTimeAsync(1);
            await flushPromises();
            expect(fetchItem).toHaveBeenCalledTimes(2);
            stop();
        });

        it("should clear backoff state on success", async () => {
            const id = "1";
            const item = { id, name: "Item 1" };
            fetchItem.mockRejectedValueOnce(new ApiError("Too Many Requests", 429)).mockResolvedValue(item);

            const { getItemById, storedItems, getItemLoadError, fetchItemById, isLoadingItem } =
                useKeyedCache<ItemData>(fetchItem);

            getItemById.value(id);
            await flushPromises();
            expect(isLoadingItem.value(id)).toBe(true);

            // An explicit fetch during the backoff succeeds; the pending retry must not keep it "loading".
            await fetchItemById({ id });
            await flushPromises();
            expect(storedItems.value[id]).toEqual(item);
            expect(getItemLoadError.value(id)).toBeNull();
            expect(isLoadingItem.value(id)).toBe(false);
        });

        it("should hide a retryable error until retries are exhausted", async () => {
            const id = "1";
            fetchItem.mockRejectedValue(new ApiError("Too Many Requests", 429));

            const { getItemById, getItemLoadError, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);
            const loadError = computed(() => getItemLoadError.value(id));
            const stop = watchEffect(() => {
                getItemById.value(id);
            });
            await flushPromises();

            for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
                // Waiting out the backoff: reported as loading, not as an error.
                expect(loadError.value).toBeNull();
                expect(isLoadingItem.value(id)).toBe(true);
                await vi.advanceTimersByTimeAsync(minDelay(attempt));
                await flushPromises();
            }
            expect(fetchItem).toHaveBeenCalledTimes(MAX_RETRIES + 1);
            expect(loadError.value).toBeInstanceOf(ApiError);
            stop();
        });

        it("should report loading while waiting out a backoff", async () => {
            const id = "1";
            fetchItem.mockRejectedValue(new ApiError("Too Many Requests", 429));

            const { getItemById, getItemLoadError, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);
            const loading = computed(() => isLoadingItem.value(id));

            getItemById.value(id);
            await flushPromises();
            expect(loading.value).toBe(true);
            expect(getItemLoadError.value(id)).toBeNull();

            await vi.advanceTimersByTimeAsync(minDelay(1) - 1);
            expect(loading.value).toBe(true);
            // Clears once the backoff elapses, so a consumer gated on it re-reads the getter.
            await vi.advanceTimersByTimeAsync(1);
            expect(loading.value).toBe(false);
        });

        it("should retry for a consumer that skips the getter while loading", async () => {
            const id = "1";
            fetchItem.mockRejectedValue(new ApiError("Too Many Requests", 429));

            const { getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);
            const stop = watchEffect(() => {
                // Mirrors templates like `v-if="isLoading || !item"`.
                return isLoadingItem.value(id) || getItemById.value(id);
            });
            await flushPromises();
            expect(fetchItem).toHaveBeenCalledTimes(1);

            await vi.advanceTimersByTimeAsync(minDelay(1));
            await flushPromises();
            expect(fetchItem).toHaveBeenCalledTimes(2);
            stop();
        });

        it("should hide a retryable error while its retry is in flight", async () => {
            const id = "1";
            fetchItem.mockRejectedValueOnce(new ApiError("Too Many Requests", 429));

            const { getItemById, getItemLoadError, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);

            getItemById.value(id);
            await flushPromises();
            fetchItem.mockReturnValueOnce(new Promise(() => {}));
            await vi.advanceTimersByTimeAsync(minDelay(1));
            getItemById.value(id);
            expect(isLoadingItem.value(id)).toBe(true);
            expect(getItemLoadError.value(id)).toBeNull();
        });
    });
});
