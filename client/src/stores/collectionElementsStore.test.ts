import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";

import { mockFetcher } from "@/schema/__mocks__";
import { useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { DCESummary, HDCASummary } from "@/stores/services";

jest.mock("@/schema");

const collection1: HDCASummary = mockCollection("1");
const collection2: HDCASummary = mockCollection("2");
const collections: HDCASummary[] = [collection1, collection2];

describe("useCollectionElementsStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        mockFetcher
            .path("/api/dataset_collections/{hdca_id}/contents/{parent_id}")
            .method("get")
            .mock(fetchCollectionElements);
    });

    it("should save collections", async () => {
        const store = useCollectionElementsStore();
        expect(store.storedCollections).toEqual({});

        store.saveCollections(collections);

        expect(store.storedCollections).toEqual({
            "1": collection1,
            "2": collection2,
        });
    });

    it("should fetch collection elements if they are not yet in the store", async () => {
        const store = useCollectionElementsStore();
        expect(store.storedCollectionElements).toEqual({});
        expect(store.isLoadingCollectionElements(collection1)).toEqual(false);

        const offset = 0;
        const limit = 5;
        // Getting collection elements should trigger a fetch
        store.getCollectionElements(collection1, offset, limit);
        expect(store.isLoadingCollectionElements(collection1)).toEqual(true);
        await flushPromises();
        expect(store.isLoadingCollectionElements(collection1)).toEqual(false);
        expect(fetchCollectionElements).toHaveBeenCalled();

        const collection1Key = store.getCollectionKey(collection1);
        const elements = store.storedCollectionElements[collection1Key];
        expect(elements).toBeDefined();
        // The total number of elements (including placeholders) is 10, but only the first 5 are fetched (real elements)
        expect(elements).toHaveLength(10);
        const nonPlaceholderElements = getRealElements(elements);
        expect(nonPlaceholderElements).toHaveLength(limit);
    });

    it("should not fetch collection elements if they are already in the store", async () => {
        const store = useCollectionElementsStore();
        const storedCount = 5;
        const expectedStoredElements = Array.from({ length: storedCount }, (_, i) => mockElement(collection1.id, i));
        const collection1Key = store.getCollectionKey(collection1);
        store.storedCollectionElements[collection1Key] = expectedStoredElements;
        expect(store.storedCollectionElements[collection1Key]).toHaveLength(storedCount);

        const offset = 0;
        const limit = 5;
        // Getting collection elements should trigger a fetch
        store.getCollectionElements(collection1, offset, limit);
        await flushPromises();
        expect(fetchCollectionElements).toHaveBeenCalled();

        fetchCollectionElements.mockClear();

        // Getting the same collection elements range should not trigger a fetch
        store.getCollectionElements(collection1, offset, limit);
        expect(store.isLoadingCollectionElements(collection1)).toEqual(false);
        expect(fetchCollectionElements).not.toHaveBeenCalled();
    });

    it("should fetch only missing elements if the requested range is not already stored", async () => {
        const store = useCollectionElementsStore();

        const initialElements = 3;
        store.getCollectionElements(collection1, 0, initialElements);
        await flushPromises();
        expect(fetchCollectionElements).toHaveBeenCalled();
        let elements = store.storedCollectionElements[collection1.id];
        // The first call will initialize the 10 placeholders and fetch the first 3 elements out of 10
        expect(elements).toHaveLength(10);
        expect(getRealElements(elements)).toHaveLength(initialElements);

        const offset = 2;
        const limit = 5;
        // Getting collection elements should trigger a fetch in this case
        store.getCollectionElements(collection1, offset, limit);
        expect(store.isLoadingCollectionElements(collection1)).toEqual(true);
        await flushPromises();
        expect(store.isLoadingCollectionElements(collection1)).toEqual(false);
        expect(fetchCollectionElements).toHaveBeenCalled();

        const collection1Key = store.getCollectionKey(collection1);
        elements = store.storedCollectionElements[collection1Key];
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
        collection_id: id,
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
        },
    };
}

interface ApiRequest {
    hdca_id: string;
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

function getRealElements(elements?: DCESummary[]): DCESummary[] | undefined {
    return elements?.filter((element) => element.id !== "placeholder");
}
