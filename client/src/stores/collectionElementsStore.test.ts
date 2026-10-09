import { getFakeCollectionSummary } from "@tests/test-data/collections";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DCESummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { type DCEEntry, useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { setupTestPinia } from "@/stores/testUtils";

const { server, http } = useServerMock();

const fetchCollectionElementsSpy = vi.fn();
describe("useCollectionElementsStore", () => {
    afterEach(() => vi.useRealTimers());
    beforeEach(() => {
        setupTestPinia();
        fetchCollectionElementsSpy.mockClear();
        server.use(
            http.get("/api/dataset_collections/{hdca_id}/contents/{parent_id}", ({ response, params, query }) => {
                const elements: DCESummary[] = [];
                const startIndex = Number(query.get("offset"));
                const limit = Number(query.get("limit"));
                const endIndex = startIndex + limit;
                for (let i = startIndex; i < endIndex; i++) {
                    elements.push(mockElement(params.hdca_id, i));
                }
                fetchCollectionElementsSpy({ collectionId: params.hdca_id, offset: startIndex, limit });
                return response(200).json(elements);
            }),
        );
    });

    it("reads an uncached collection without fetching until a range is requested", async () => {
        const totalElements = 10;
        const collection = getFakeCollectionSummary({ id: "1", element_count: totalElements });
        const store = useCollectionElementsStore();
        expect(store.storedCollectionElements).toEqual({});
        expect(store.isLoadingCollectionElements(collection)).toBe(false);

        expect(store.getCollectionElements(collection)).toBeUndefined();
        expect(store.isLoadingCollectionElements(collection)).toBe(false);
        await flushPromises();
        expect(fetchCollectionElementsSpy).not.toHaveBeenCalled();

        const limit = 5;
        store.fetchMissingElements(collection, 0, limit);
        await flushPromises();
        expect(fetchCollectionElementsSpy).toHaveBeenCalledExactlyOnceWith({ collectionId: "1", offset: 0, limit });

        const collectionKey = store.getCollectionKey(collection);
        const elements = store.storedCollectionElements[collectionKey];
        expect(elements).toBeDefined();
        expect(elements).toHaveLength(totalElements);
        const fetchedElements = getFetchedElements(elements);
        expect(fetchedElements).toHaveLength(limit);
    });

    it("does not fetch a requested range that is already cached", async () => {
        const totalElements = 10;
        const collection = getFakeCollectionSummary({ id: "1", element_count: totalElements });
        const store = useCollectionElementsStore();
        const storedCount = 5;
        const expectedStoredElements = Array.from({ length: storedCount }, (_, i) => mockElement(collection.id, i));
        const collectionKey = store.getCollectionKey(collection);
        store.storedCollectionElements[collectionKey] = expectedStoredElements;
        expect(store.storedCollectionElements[collectionKey]).toHaveLength(storedCount);

        const offset = 0;
        const limit = storedCount;
        store.fetchMissingElements(collection, offset, limit);
        expect(store.isLoadingCollectionElements(collection)).toBe(false);
        await flushPromises();
        expect(store.isLoadingCollectionElements(collection)).toBe(false);
        expect(fetchCollectionElementsSpy).not.toHaveBeenCalled();
    });

    it("starts an overlapping request at the first missing element", async () => {
        vi.useFakeTimers();

        const totalElements = 10;
        const collection = getFakeCollectionSummary({ id: "1", element_count: totalElements });
        const store = useCollectionElementsStore();

        const initialElements = 3;
        store.fetchMissingElements(collection, 0, initialElements);
        await flushPromises();
        expect(fetchCollectionElementsSpy).toHaveBeenCalledExactlyOnceWith({
            collectionId: "1",
            offset: 0,
            limit: initialElements,
        });
        const collectionKey = store.getCollectionKey(collection);
        let elements = store.storedCollectionElements[collectionKey];
        expect(elements).toHaveLength(totalElements);
        expect(getFetchedElements(elements)).toHaveLength(initialElements);

        const offset = 2;
        const limit = 5;
        store.fetchMissingElements(collection, offset, limit);
        vi.runAllTimers();
        await flushPromises();
        expect(fetchCollectionElementsSpy).toHaveBeenCalledTimes(2);
        // The request overlaps element 2, so fetching starts at the first missing index, 3.
        expect(fetchCollectionElementsSpy).toHaveBeenLastCalledWith({ collectionId: "1", offset: 3, limit });

        elements = store.storedCollectionElements[collectionKey];
        expect(elements).toBeDefined();
        expect(elements).toHaveLength(10);
        expect(getFetchedElements(elements)).toHaveLength(initialElements + limit);
    });
});

function mockElement(collectionId: string, i: number): DCESummary {
    const fakeID = `${collectionId}-${i}`;
    return {
        id: fakeID,
        element_index: i,
        element_identifier: `element ${i}`,
        element_type: "hda",
        model_class: "DatasetCollectionElement",
        object: {
            id: fakeID,
            model_class: "HistoryDatasetAssociation",
            state: "ok",
            hda_ldda: "hda",
            history_id: "1",
            tags: [],
            accessible: true,
            purged: false,
        },
    };
}

function getFetchedElements(elements?: DCEEntry[]): DCESummary[] | undefined {
    return elements?.filter((element): element is DCESummary => "id" in element);
}
