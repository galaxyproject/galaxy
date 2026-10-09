import { getFakeCollectionSummary } from "@tests/test-data/collections";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
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

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
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

    it("fetches elements added to a collection after its elements were stored", async () => {
        vi.useFakeTimers();
        const collection = getFakeCollectionSummary({ id: "1", element_count: 0 });
        const store = useCollectionElementsStore();

        // Opened while the collection was still populating.
        await store.fetchMissingElements(collection, 0);
        expect(store.getCollectionElements(collection)).toEqual([]);

        collection.element_count = 3;
        store.fetchMissingElements(collection, 0, 3);
        await vi.advanceTimersByTimeAsync(1500);
        await flushPromises();

        expect(getFetchedElements(store.getCollectionElements(collection))).toHaveLength(3);
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
        const collection = getFakeCollectionSummary({ id: "1", element_count: 3 });

        await store.fetchMissingElements(collection, 0);
        expect(store.getLoadingCollectionElementsError(collection)).toBeInstanceOf(Error);

        failRequest = false;
        store.fetchMissingElements(collection, 0);
        await vi.advanceTimersByTimeAsync(1500);
        await flushPromises();

        expect(store.getLoadingCollectionElementsError(collection)).toBe(false);
        expect(getFetchedElements(store.getCollectionElements(collection))).toHaveLength(3);
    });

    it("reports a 5xx error fetching collection elements immediately", async () => {
        vi.spyOn(console, "error").mockImplementation(() => {});
        server.use(
            http.get("/api/dataset_collections/{hdca_id}/contents/{parent_id}", ({ response }) =>
                response("5XX").json({ err_msg: "Internal Server Error", err_code: 0 }, { status: 500 }),
            ),
        );
        const store = useCollectionElementsStore();
        const collection = getFakeCollectionSummary({ id: "1", element_count: 5 });

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
        const collection = getFakeCollectionSummary({ id: "1", element_count: 3 });

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
        const elements = getFetchedElements(store.getCollectionElements(collection));
        expect(elements?.map((element) => (element.object as { state: string }).state)).toEqual(["ok", "ok", "ok"]);
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
