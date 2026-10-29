import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DCESummary, HDCASummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { type DCEEntry, useCollectionElementsStore } from "@/stores/collectionElementsStore";

// The "should save collections" test moved to `datasetCollectionStore.test.ts`
// when detail / summary caching was split out.

const { server, http } = useServerMock();

const fetchCollectionElementsSpy = vi.fn();
describe("useCollectionElementsStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        fetchCollectionElementsSpy.mockClear();
        server.use(
            http.get("/api/dataset_collections/{hdca_id}/contents/{parent_id}", ({ response, params, query }) => {
                const elements: DCESummary[] = [];
                const startIndex = Number(query.get("offset"));
                const endIndex = startIndex + Number(query.get("limit"));
                for (let i = startIndex; i < endIndex; i++) {
                    elements.push(mockElement(params.hdca_id, i));
                }
                fetchCollectionElementsSpy();
                return response(200).json(elements);
            }),
        );
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
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
        expect(fetchCollectionElementsSpy).not.toHaveBeenCalled();

        const limit = 5;
        store.fetchMissingElements(collection, 0, limit);
        await flushPromises();
        expect(fetchCollectionElementsSpy).toHaveBeenCalled();

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
        expect(fetchCollectionElementsSpy).not.toHaveBeenCalled();
    });

    it("should fetch only missing elements if the requested range is not already stored", async () => {
        vi.useFakeTimers();

        const totalElements = 10;
        const collection: HDCASummary = mockCollection("1", totalElements);
        const store = useCollectionElementsStore();

        const initialElements = 3;
        store.fetchMissingElements(collection, 0, initialElements);
        await flushPromises();
        expect(fetchCollectionElementsSpy).toHaveBeenCalled();
        const collectionKey = store.getCollectionKey(collection);
        let elements = store.storedCollectionElements[collectionKey];
        // The first call will initialize the 10 placeholders and fetch the first 3 elements out of 10
        expect(elements).toHaveLength(totalElements);
        expect(getRealElements(elements)).toHaveLength(initialElements);

        const offset = 2;
        const limit = 5;
        // Fetching collection elements should trigger a fetch in this case
        store.fetchMissingElements(collection, offset, limit);
        vi.runAllTimers();
        await flushPromises();
        expect(fetchCollectionElementsSpy).toHaveBeenCalled();

        elements = store.storedCollectionElements[collectionKey];
        expect(elements).toBeDefined();
        expect(elements).toHaveLength(10);
        // The offset was overlapping with the stored elements, so it was increased by the number of stored elements
        // and it fetches the next "limit" number of elements
        expect(getRealElements(elements)).toHaveLength(initialElements + limit);
    });

    it("fetches elements added to a collection after its elements were stored", async () => {
        vi.useFakeTimers();
        const collection: HDCASummary = mockCollection("1", 0);
        const store = useCollectionElementsStore();

        // Opened while the collection was still populating.
        await store.fetchMissingElements(collection, 0);
        expect(store.getCollectionElements(collection)).toEqual([]);

        collection.element_count = 3;
        store.fetchMissingElements(collection, 0, 3);
        await vi.advanceTimersByTimeAsync(1500);
        await flushPromises();

        expect(getRealElements(store.getCollectionElements(collection))).toHaveLength(3);
    });
});

describe("useCollectionElementsStore element loading errors", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    it("clears an error fetching collection elements once a later fetch succeeds", async () => {
        vi.useFakeTimers();
        vi.spyOn(console, "error").mockImplementation(() => {});
        let failRequest = true;
        server.use(
            http.get("/api/dataset_collections/{hdca_id}/contents/{parent_id}", ({ response, params }) => {
                if (failRequest) {
                    return response("5XX").json({ err_msg: "Bad Gateway", err_code: 0 }, { status: 502 });
                }
                return response(200).json([0, 1, 2].map((i) => mockElement(params.hdca_id, i)));
            }),
        );
        const store = useCollectionElementsStore();
        const collection = mockCollection("1", 3);

        await store.fetchMissingElements(collection, 0);
        expect(store.getLoadingCollectionElementsError(collection)).toBeInstanceOf(Error);

        failRequest = false;
        store.fetchMissingElements(collection, 0);
        await vi.advanceTimersByTimeAsync(1500);
        await flushPromises();

        expect(store.getLoadingCollectionElementsError(collection)).toBe(false);
        expect(getRealElements(store.getCollectionElements(collection))).toHaveLength(3);
    });

    it("reports a 5xx error fetching collection elements immediately", async () => {
        vi.spyOn(console, "error").mockImplementation(() => {});
        server.use(
            http.get("/api/dataset_collections/{hdca_id}/contents/{parent_id}", ({ response }) =>
                response("5XX").json({ err_msg: "Internal Server Error", err_code: 0 }, { status: 500 }),
            ),
        );
        const store = useCollectionElementsStore();
        const collection = mockCollection("1", 5);

        await store.fetchMissingElements(collection, 0);
        expect(store.getLoadingCollectionElementsError(collection)).toBeInstanceOf(Error);
    });
});

describe("useCollectionElementsStore invalidation", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("refetches elements invalidated while a fetch of them is in flight", async () => {
        let serverState = "running";
        let releaseResponse = () => {};
        let holdResponse = false;
        const requestedStates: string[] = [];
        server.use(
            http.get("/api/dataset_collections/{hdca_id}/contents/{parent_id}", async ({ response, params }) => {
                // The response reflects the state at the time the request reached the server.
                const state = serverState;
                requestedStates.push(state);
                if (holdResponse) {
                    await new Promise<void>((resolve) => (releaseResponse = resolve));
                }
                const elements = [0, 1, 2].map((i) => ({
                    ...mockElement(params.hdca_id, i),
                    object: { ...mockElement(params.hdca_id, i).object, state },
                }));
                return response(200).json(elements as DCESummary[]);
            }),
        );
        const store = useCollectionElementsStore();
        const collection = mockCollection("1", 3);

        await store.fetchMissingElements(collection, 0);
        await vi.advanceTimersByTimeAsync(1500);

        // A refresh starts, and the server answers it before the elements finish.
        holdResponse = true;
        store.invalidateCollectionElements(collection);
        store.fetchMissingElements(collection, 0);
        await vi.advanceTimersByTimeAsync(0);
        expect(requestedStates).toEqual(["running", "running"]);

        // The elements finish and the history watcher reports it before that response arrives.
        holdResponse = false;
        serverState = "ok";
        store.invalidateCollectionElements(collection);
        store.fetchMissingElements(collection, 0);
        releaseResponse();
        await vi.advanceTimersByTimeAsync(1500);
        await flushPromises();

        expect(requestedStates).toEqual(["running", "running", "ok"]);
        const elements = getRealElements(store.getCollectionElements(collection));
        expect(elements?.map((element) => (element.object as { state: string }).state)).toEqual(["ok", "ok", "ok"]);
    });
});

function mockCollection(id: string, numElements = 10): HDCASummary {
    return {
        id: id,
        element_count: numElements,
        elements_datatypes: ["txt"],
        elements_deleted: 0,
        elements_states: {},
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
        type: "collection",
        store_times_summary: null,
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

/**
 * Filter out the placeholder elements from the given array.
 */
function getRealElements(elements?: DCEEntry[]): DCESummary[] | undefined {
    return elements?.filter((element) => "id" in element === true) as DCESummary[];
}
