import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";

import type { DCESummary, HDCASummary } from "@/api";
import { mockFetcher } from "@/api/schema/__mocks__";
import { DCEEntry, useCollectionElementsStore } from "@/stores/collectionElementsStore";

jest.mock("@/api/schema");

describe("useCollectionElementsStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        mockFetcher
            .path("/api/dataset_collections/{hdca_id}/contents/{parent_id}")
            .method("get")
            .mock(fetchCollectionElements);
    });

    it("should save collections", async () => {
        const collection1: HDCASummary = mockCollection("1");
        const collection2: HDCASummary = mockCollection("2");
        const collections: HDCASummary[] = [collection1, collection2];
        const store = useCollectionElementsStore();
        expect(store.storedCollections).toEqual({});

        store.saveCollections(collections);

        expect(store.storedCollections).toEqual({
            "1": collection1,
            "2": collection2,
        });
    });

    it("should fetch collection elements if they are not yet in the store", async () => {
        const totalElements = 10;
        const collection: HDCASummary = mockCollection("1", totalElements);
        const store = useCollectionElementsStore();
        expect(store.storedCollectionElements).toEqual({});
        expect(store.isLoadingCollectionElements(collection)).toEqual(false);

        // Getting collection elements should be side effect free
        store.getCollectionElements(collection);
        expect(store.isLoadingCollectionElements(collection)).toEqual(false);
        await flushPromises();
        expect(fetchCollectionElements).not.toHaveBeenCalled();

        const limit = 5;
        store.fetchMissingElements(collection, 0, limit);
        await flushPromises();
        expect(fetchCollectionElements).toHaveBeenCalled();

        const collectionKey = store.getCollectionKey(collection);
        const elements = store.storedCollectionElements[collectionKey];
        expect(elements).toBeDefined();
        // The total number of elements (including placeholders) is 10, but only the first 5 are fetched (real elements)
        expect(elements).toHaveLength(totalElements);
        const nonPlaceholderElements = getRealElements(elements);
        expect(nonPlaceholderElements).toHaveLength(limit);
    });

    it("should not fetch collection elements if they are already in the store", async () => {
        const totalElements = 10;
        const collection: HDCASummary = mockCollection("1", totalElements);
        const store = useCollectionElementsStore();
        // Prefill the store with the first 5 elements
        const storedCount = 5;
        const expectedStoredElements = Array.from({ length: storedCount }, (_, i) => mockElement(collection.id, i));
        const collectionKey = store.getCollectionKey(collection);
        store.storedCollectionElements[collectionKey] = expectedStoredElements;
        expect(store.storedCollectionElements[collectionKey]).toHaveLength(storedCount);

        const offset = 0;
        const limit = storedCount;
        // Getting the same collection elements range should not trigger a fetch
        store.fetchMissingElements(collection, offset, limit);
        expect(store.isLoadingCollectionElements(collection)).toEqual(false);
        expect(fetchCollectionElements).not.toHaveBeenCalled();
    });

    it("should fetch only missing elements if the requested range is not already stored", async () => {
        jest.useFakeTimers();

        const totalElements = 10;
        const collection: HDCASummary = mockCollection("1", totalElements);
        const store = useCollectionElementsStore();

        const initialElements = 3;
        store.fetchMissingElements(collection, 0, initialElements);
        await flushPromises();
        expect(fetchCollectionElements).toHaveBeenCalled();
        const collectionKey = store.getCollectionKey(collection);
        let elements = store.storedCollectionElements[collectionKey];
        // The first call will initialize the 10 placeholders and fetch the first 3 elements out of 10
        expect(elements).toHaveLength(totalElements);
        expect(getRealElements(elements)).toHaveLength(initialElements);

        const offset = 2;
        const limit = 5;
        // Fetching collection elements should trigger a fetch in this case
        store.fetchMissingElements(collection, offset, limit);
        jest.runAllTimers();
        await flushPromises();
        expect(fetchCollectionElements).toHaveBeenCalled();

        elements = store.storedCollectionElements[collectionKey];
        expect(elements).toBeDefined();
        expect(elements).toHaveLength(10);
        // The offset was overlapping with the stored elements, so it was increased by the number of stored elements
        // and it fetches the next "limit" number of elements
        expect(getRealElements(elements)).toHaveLength(initialElements + limit);
    });
});

function mockCollection(id: string, numElements = 10): HDCASummary {
    return {
        id: id,
        element_count: numElements,
        collection_type: "list",
        populated_state: "ok",
        populated_state_message: "",
        collection_id: `DC_ID_${id}`,
        name: `collection ${id}`,
        deleted: false,
        contents_url: "",
        hid: 1,
        history_content_type: "dataset_collection",
        history_id: "1",
        model_class: "HistoryDatasetCollectionAssociation",
        tags: [],
        visible: true,
        create_time: "2021-05-25T14:00:00.000Z",
        update_time: "2021-05-25T14:00:00.000Z",
        type_id: "dataset_collection",
        url: "",
    };
}

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

interface ApiRequest {
    hdca_id: string;
    parent_id: string;
    offset: number;
    limit: number;
}

const fetchCollectionElements = jest.fn(fakeCollectionElementsApiResponse);

function fakeCollectionElementsApiResponse(params: ApiRequest) {
    const elements: DCESummary[] = [];
    const startIndex = params.offset ?? 0;
    const endIndex = startIndex + (params.limit ?? 10);
    for (let i = startIndex; i < endIndex; i++) {
        elements.push(mockElement(params.hdca_id, i));
    }
    return {
        data: elements,
    };
}

/**
 * Filter out the placeholder elements from the given array.
 */
function getRealElements(elements?: DCEEntry[]): DCESummary[] | undefined {
    return elements?.filter((element) => "id" in element === true) as DCESummary[];
}
