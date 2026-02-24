import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed, ref } from "vue";

import { ApiError } from "@/utils/simple-error";

import { useKeyedCache } from "./keyedCache";

interface ItemData {
    id: string;
    name: string;
}

const fetchItem = vi.fn();
const shouldFetch = vi.fn();

describe("useKeyedCache", () => {
    beforeEach(() => {
        fetchItem.mockClear();
        shouldFetch.mockClear();
    });

    it("should fetch the item if it is not already stored", async () => {
        const id = "1";
        const item = { id: id, name: "Item 1" };
        const fetchParams = { id: id };

        fetchItem.mockResolvedValue(item);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);

        expect(storedItems.value).toEqual({});
        expect(isLoadingItem.value(id)).toBeFalsy();

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBeTruthy();
        await flushPromises();
        expect(isLoadingItem.value(id)).toBeFalsy();
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
    });

    it("should not fetch the item if it is already stored", async () => {
        const id = "1";
        const item = { id: id, name: "Item 1" };

        fetchItem.mockResolvedValue(item);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);

        storedItems.value[id] = item;

        expect(isLoadingItem.value(id)).toBeFalsy();

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBeFalsy();
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).not.toHaveBeenCalled();
    });

    it("should not fetch if the stored item is 0 (or any falsy value)", async () => {
        const id = "1";
        const item = 0;

        fetchItem.mockResolvedValue(item);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<number>(fetchItem);

        storedItems.value[id] = item;

        expect(isLoadingItem.value(id)).toBeFalsy();

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBeFalsy();
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).not.toHaveBeenCalled();
    });

    it("should fetch the item regardless of whether it is already stored if shouldFetch returns true", async () => {
        const id = "1";
        const item = { id: id, name: "Item 1" };
        const fetchParams = { id: id };

        fetchItem.mockResolvedValue(item);
        shouldFetch.mockReturnValue(() => true);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem, shouldFetch);

        storedItems.value[id] = item;

        expect(isLoadingItem.value(id)).toBeFalsy();

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBeTruthy();
        await flushPromises();
        expect(isLoadingItem.value(id)).toBeFalsy();
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
        expect(shouldFetch).toHaveBeenCalled();
    });

    it("should not fetch the item if it is already being fetched", async () => {
        const id = "1";
        const item = { id: id, name: "Item 1" };
        const fetchParams = { id: id };

        fetchItem.mockResolvedValue(item);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);

        expect(isLoadingItem.value(id)).toBeFalsy();

        getItemById.value(id);
        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBeTruthy();
        await flushPromises();
        expect(isLoadingItem.value(id)).toBeFalsy();
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledTimes(1);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
    });

    it("should not fetch the item if it is already being fetched, even if shouldFetch returns true", async () => {
        const id = "1";
        const item = { id: id, name: "Item 1" };
        const fetchParams = { id: id };

        fetchItem.mockResolvedValue(item);
        shouldFetch.mockReturnValue(() => true);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem, shouldFetch);

        expect(isLoadingItem.value(id)).toBeFalsy();

        getItemById.value(id);
        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBeTruthy();
        await flushPromises();
        expect(isLoadingItem.value(id)).toBeFalsy();
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledTimes(1);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
        expect(shouldFetch).toHaveBeenCalled();
    });

    it("should accept a ref for fetchItem", async () => {
        const id = "1";
        const item = { id: id, name: "Item 1" };
        const fetchParams = { id: id };

        fetchItem.mockResolvedValue(item);

        const fetchItemRef = ref(fetchItem);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItemRef);

        expect(isLoadingItem.value(id)).toBeFalsy();

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBeTruthy();
        await flushPromises();
        expect(isLoadingItem.value(id)).toBeFalsy();
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
    });

    it("should accept a computed for shouldFetch", async () => {
        const id = "1";
        const item = { id: id, name: "Item 1" };
        const fetchParams = { id: id };

        fetchItem.mockResolvedValue(item);
        shouldFetch.mockReturnValue(true);

        const shouldFetchComputed = computed(() => shouldFetch);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem, shouldFetchComputed);

        expect(isLoadingItem.value(id)).toBeFalsy();

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBeTruthy();
        await flushPromises();
        expect(isLoadingItem.value(id)).toBeFalsy();
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams, expect.anything());
        expect(shouldFetch).toHaveBeenCalled();
    });

    it("should not re-fetch after a failed request", async () => {
        const id = "1";

        fetchItem.mockRejectedValue(new Error("Request failed"));

        const { getItemById, getItemLoadError, isLoadingItem } = useKeyedCache<ItemData>(fetchItem);

        getItemById.value(id);
        await flushPromises();

        expect(isLoadingItem.value(id)).toBeFalsy();
        expect(getItemLoadError.value(id)).toBeInstanceOf(Error);
        expect(fetchItem).toHaveBeenCalledTimes(1);

        // Calling getItemById again should not trigger another fetch
        getItemById.value(id);
        await flushPromises();

        expect(fetchItem).toHaveBeenCalledTimes(1);
    });

    it("should retry on transient errors (429, 5xx) up to max retries", async () => {
        const id = "1";

        fetchItem.mockRejectedValue(new ApiError("Too Many Requests", 429));

        const { getItemById, getItemLoadError } = useKeyedCache<ItemData>(fetchItem);

        // First attempt + MAX_RETRIES - 1 retries (first call counts as attempt 1)
        for (let i = 1; i <= 3; i++) {
            getItemById.value(id);
            await flushPromises();
            expect(fetchItem).toHaveBeenCalledTimes(i);
            expect(getItemLoadError.value(id)).toBeInstanceOf(ApiError);
        }

        // Should stop after max retries exhausted
        getItemById.value(id);
        await flushPromises();
        expect(fetchItem).toHaveBeenCalledTimes(3);
    });

    it("should not retry on permanent errors (403, 404)", async () => {
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

    it("should recover on retry if transient error resolves", async () => {
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

    it("should handle fake timers without hanging when advanced manually", async () => {
        vi.useFakeTimers();
        const id = "1";
        const item = { id, name: "Item 1" };
        fetchItem.mockImplementation(() => {
            return new Promise((resolve) => {
                setTimeout(() => resolve(item), 10);
            });
        });
        const { getItemById } = useKeyedCache<ItemData>(fetchItem);
        getItemById.value(id);
        getItemById.value(id);
        getItemById.value(id);
        await flushPromises();
        vi.runOnlyPendingTimers();
        await flushPromises();
        expect(true).toBe(true);
    });
});
