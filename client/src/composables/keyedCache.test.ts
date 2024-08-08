import flushPromises from "flush-promises";
import { computed, ref } from "vue";

import { useKeyedCache } from "./keyedCache";

interface ItemData {
    id: string;
    name: string;
}

const fetchItem = jest.fn();
const shouldFetch = jest.fn();

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
        expect(fetchItem).toHaveBeenCalledWith(fetchParams);
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
        expect(fetchItem).toHaveBeenCalledWith(fetchParams);
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
        expect(fetchItem).toHaveBeenCalledWith(fetchParams);
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
        expect(fetchItem).toHaveBeenCalledWith(fetchParams);
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
        expect(fetchItem).toHaveBeenCalledWith(fetchParams);
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
        expect(fetchItem).toHaveBeenCalledWith(fetchParams);
        expect(shouldFetch).toHaveBeenCalled();
    });
});
