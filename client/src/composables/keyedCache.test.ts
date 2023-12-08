import flushPromises from "flush-promises";

import { useKeyedCache } from "./keyedCache";

interface ItemData {
    id: string;
    name: string;
}

const fetchItem = jest.fn();
const shouldFetch = jest.fn();

describe("useSimpleKeyStore", () => {
    beforeEach(() => {
        fetchItem.mockClear();
        shouldFetch.mockClear();
    });

    it("should fetch the item if it is not already stored", async () => {
        const id = "1";
        const item = { id: id, name: "Item 1" };
        const fetchParams = { id: id };
        const apiResponse = { data: item };

        fetchItem.mockResolvedValue(apiResponse);

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

        fetchItem.mockResolvedValue({ data: item });

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
        const apiResponse = { data: item };

        fetchItem.mockResolvedValue(apiResponse);
        shouldFetch.mockReturnValue(true);

        const { storedItems, getItemById, isLoadingItem } = useKeyedCache<ItemData>(fetchItem, shouldFetch);

        storedItems.value[id] = item;

        expect(isLoadingItem.value(id)).toBeFalsy();

        getItemById.value(id);

        expect(isLoadingItem.value(id)).toBeTruthy();
        await flushPromises();
        expect(isLoadingItem.value(id)).toBeFalsy();
        expect(storedItems.value[id]).toEqual(item);
        expect(fetchItem).toHaveBeenCalledWith(fetchParams);
    });
});
