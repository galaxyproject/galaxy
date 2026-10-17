import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { HDCADetailed, HDCASummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { MAX_RETRIES } from "@/utils/simple-error";

import { useDatasetCollectionStore } from "./datasetCollectionStore";

const { server, http } = useServerMock();

const fetchSpy = vi.fn();

const RETRY_BACKOFF_BASE_MS = 2000;
const RETRY_BACKOFF_CAP_MS = 30_000;

describe("useDatasetCollectionStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        fetchSpy.mockClear();
        server.use(
            http.get("/api/dataset_collections/{hdca_id}", ({ response, params }) => {
                fetchSpy();
                return response(200).json(mockDetailedCollection(params.hdca_id as string));
            }),
        );
    });

    it("saveCollections populates the cache from a history-contents payload", () => {
        const a: HDCASummary = mockSummaryCollection("1");
        const b: HDCASummary = mockSummaryCollection("2");
        const store = useDatasetCollectionStore();
        expect(store.storedCollections).toEqual({});

        store.saveCollections([a, b]);

        expect(store.storedCollections).toEqual({ "1": a, "2": b });
    });

    it("saveCollections ignores non-collection history entries", () => {
        const collection: HDCASummary = mockSummaryCollection("1");
        // The function signature accepts HistoryContentItemBase[]; in practice
        // the payload mixes datasets and collections.
        const dataset = { id: "ds-1", history_content_type: "dataset" } as never;
        const store = useDatasetCollectionStore();

        store.saveCollections([collection, dataset]);

        expect(Object.keys(store.storedCollections)).toEqual(["1"]);
    });

    it("getCollection returns summary without triggering a fetch when cached", async () => {
        const summary: HDCASummary = mockSummaryCollection("1");
        const store = useDatasetCollectionStore();
        store.saveCollection(summary);

        const result = store.getCollection("1");
        await flushPromises();

        expect(result).toEqual(summary);
        expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("getCollection triggers a fetch when nothing is cached", async () => {
        const store = useDatasetCollectionStore();

        const first = store.getCollection("1");
        expect(first).toBeNull();
        await flushPromises();

        expect(fetchSpy).toHaveBeenCalledTimes(1);
        // After the fetch lands the next read returns the detail.
        const second = store.getCollection("1");
        expect(second).not.toBeNull();
        expect("elements" in second!).toBe(true);
    });

    it("getDetailedCollection upgrades a summary by fetching detail", async () => {
        const summary: HDCASummary = mockSummaryCollection("1");
        const store = useDatasetCollectionStore();
        store.saveCollection(summary);

        // First read returns the currently-cached summary while the upgrade is
        // in flight; shouldFetch fires because the entry isn't yet detailed.
        store.getDetailedCollection("1");
        await flushPromises();

        expect(fetchSpy).toHaveBeenCalledTimes(1);
        const upgraded = store.getDetailedCollection("1");
        expect(upgraded).not.toBeNull();
        expect("elements" in upgraded!).toBe(true);
    });

    it("getDetailedCollection does not refetch once detail is cached", async () => {
        const store = useDatasetCollectionStore();

        store.getDetailedCollection("1");
        await flushPromises();
        expect(fetchSpy).toHaveBeenCalledTimes(1);

        store.getDetailedCollection("1");
        await flushPromises();
        expect(fetchSpy).toHaveBeenCalledTimes(1);
    });
});

describe("useDatasetCollectionStore load errors", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.useFakeTimers();
        // Lowest jitter: the first backoff is RETRY_BACKOFF_BASE_MS / 2.
        vi.spyOn(Math, "random").mockReturnValue(0);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    it("waits out a backoff before refetching a collection after a retryable error", async () => {
        let requests = 0;
        server.use(
            http.get("/api/dataset_collections/{hdca_id}", ({ response }) => {
                requests += 1;
                return response("5XX").json({ err_msg: "Service Unavailable", err_code: 0 }, { status: 503 });
            }),
        );
        const store = useDatasetCollectionStore();

        store.getCollection("hdca-1");
        await flushPromises();
        expect(requests).toBe(1);

        store.getCollection("hdca-1");
        store.getDetailedCollection("hdca-1");
        await flushPromises();
        expect(requests).toBe(1);

        await vi.advanceTimersByTimeAsync(RETRY_BACKOFF_BASE_MS / 2);
        store.getDetailedCollection("hdca-1");
        await flushPromises();
        expect(requests).toBe(2);
    });

    it("waits out Retry-After before refetching a collection", async () => {
        let requests = 0;
        server.use(
            http.get("/api/dataset_collections/{hdca_id}", ({ response }) => {
                requests += 1;
                return response("5XX").json(
                    { err_msg: "Service Unavailable", err_code: 0 },
                    { status: 503, headers: { "Retry-After": "10" } },
                );
            }),
        );
        const store = useDatasetCollectionStore();

        store.getDetailedCollection("hdca-1");
        await flushPromises();
        await vi.advanceTimersByTimeAsync(9_999);
        store.getDetailedCollection("hdca-1");
        await flushPromises();
        expect(requests).toBe(1);

        await vi.advanceTimersByTimeAsync(1);
        store.getDetailedCollection("hdca-1");
        await flushPromises();
        expect(requests).toBe(2);
    });

    it("keeps a failed collection fetch out of the elements state of a collection with the same key", async () => {
        server.use(
            http.get("/api/dataset_collections/{hdca_id}", ({ response }) =>
                response("5XX").json({ err_msg: "Service Unavailable", err_code: 0 }, { status: 503 }),
            ),
        );
        const store = useDatasetCollectionStore();
        const elementsStore = useCollectionElementsStore();
        // Encoded HDCA and dataset collection ids share one id space, so they can coincide.
        const otherCollection = { ...mockSummaryCollection("other"), collection_id: "shared-id" };

        for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            store.getDetailedCollection("shared-id");
            await flushPromises();
            expect(elementsStore.isLoadingCollectionElements(otherCollection)).toBe(false);
            await vi.advanceTimersByTimeAsync(RETRY_BACKOFF_CAP_MS);
        }
        expect(elementsStore.getLoadingCollectionElementsError(otherCollection)).toBe(false);
    });
});

function mockSummaryCollection(id: string, numElements = 10): HDCASummary {
    return {
        id,
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

function mockDetailedCollection(id: string): HDCADetailed {
    return {
        ...mockSummaryCollection(id),
        elements: [],
    } as HDCADetailed;
}
