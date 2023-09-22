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

        store.saveCollectionObjects(collections);

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

        const elements = store.storedCollectionElements[collection1.id];
        expect(elements).toBeDefined();
        expect(elements).toHaveLength(limit);
    });

    it("should not fetch collection elements if they are already in the store", async () => {
        const store = useCollectionElementsStore();
        const storedCount = 5;
        const expectedStoredElements = Array.from({ length: storedCount }, (_, i) => mockElement(collection1.id, i));
        store.storedCollectionElements[collection1.id] = expectedStoredElements;
        expect(store.storedCollectionElements[collection1.id]).toHaveLength(storedCount);

        const offset = 0;
        const limit = 5;
        // Getting collection elements should not trigger a fetch in this case
        store.getCollectionElements(collection1, offset, limit);
        expect(store.isLoadingCollectionElements(collection1)).toEqual(false);
        expect(fetchCollectionElements).not.toHaveBeenCalled();
    });

    it("should fetch only missing elements if the requested range is not already stored", async () => {
        const store = useCollectionElementsStore();
        const storedCount = 3;
        const expectedStoredElements = Array.from({ length: storedCount }, (_, i) => mockElement(collection1.id, i));
        store.storedCollectionElements[collection1.id] = expectedStoredElements;
        expect(store.storedCollectionElements[collection1.id]).toHaveLength(storedCount);

        const offset = 2;
        const limit = 5;
        // Getting collection elements should trigger a fetch in this case
        store.getCollectionElements(collection1, offset, limit);
        expect(store.isLoadingCollectionElements(collection1)).toEqual(true);
        await flushPromises();
        expect(store.isLoadingCollectionElements(collection1)).toEqual(false);
        expect(fetchCollectionElements).toHaveBeenCalled();

        const elements = store.storedCollectionElements[collection1.id];
        expect(elements).toBeDefined();
        // The offset was overlapping with the stored elements, so it was increased by the number of stored elements
        // so it fetches the next "limit" number of elements
        expect(elements).toHaveLength(storedCount + limit);
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
