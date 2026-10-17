import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, ref } from "vue";

import { ApiError } from "@/utils/simple-error";

import { type FetchParams, useKeyedCache } from "./keyedCache";

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
        const id = "1";

        fetchItem.mockRejectedValue(new ApiError("Too Many Requests", 429));

        const { getItemById, getItemLoadError } = useKeyedCache<ItemData>(fetchItem);

        // Initial fetch + MAX_RETRIES retries = 4 total calls
        for (let i = 1; i <= 4; i++) {
            getItemById.value(id);
            await flushPromises();
            expect(fetchItem).toHaveBeenCalledTimes(i);
            expect(getItemLoadError.value(id)).toBeInstanceOf(ApiError);
        }

        // Should stop after max retries exhausted
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
        const id = "1";
        const item = { id, name: "Item 1" };

        fetchItem.mockRejectedValueOnce(new ApiError("Service Unavailable", 503)).mockResolvedValueOnce(item);

        const { getItemById, storedItems, getItemLoadError } = useKeyedCache<ItemData>(fetchItem);

        getItemById.value(id);
        await flushPromises();
        expect(fetchItem).toHaveBeenCalledTimes(1);
        expect(getItemLoadError.value(id)).toBeInstanceOf(ApiError);

        // Retry should succeed
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
        const id = "1";
        const item = { id, name: "Item 1" };
        fetchItem.mockRejectedValueOnce(new ApiError("service unavailable", 503));
        fetchItem.mockResolvedValue(item);

        const { getItemById, storedItems, getItemLoadError } = useKeyedCache<ItemData>(fetchItem);

        getItemById.value(id);
        await flushPromises();
        expect(getItemLoadError.value(id)).toBeInstanceOf(ApiError);

        getItemById.value(id);
        await flushPromises();
        expect(storedItems.value[id]).toEqual(item);
        expect(getItemLoadError.value(id)).toBeNull();
    });
});
