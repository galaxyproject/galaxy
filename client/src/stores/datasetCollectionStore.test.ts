import { getFakeCollectionSummary } from "@tests/test-data/collections";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { HDCADetailed, HistoryContentItemBase } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { MAX_RETRIES } from "@/utils/simple-error";

import { useDatasetCollectionStore } from "./datasetCollectionStore";
import { setupTestPinia } from "./testUtils";

const { server, http } = useServerMock();

const fetchSpy = vi.fn();

const RETRY_BACKOFF_BASE_MS = 2000;
const RETRY_BACKOFF_CAP_MS = 30_000;

describe("useDatasetCollectionStore", () => {
    beforeEach(() => {
        setupTestPinia();
        fetchSpy.mockClear();
        server.use(
            http.get("/api/dataset_collections/{hdca_id}", ({ response, params }) => {
                fetchSpy();
                return response(200).json(mockDetailedCollection(params.hdca_id));
            }),
        );
    });

    it("saveCollections populates the cache from a history-contents payload", () => {
        const firstCollection = getFakeCollectionSummary({ id: "1" });
        const secondCollection = getFakeCollectionSummary({ id: "2" });
        const store = useDatasetCollectionStore();
        expect(store.storedCollections).toEqual({});

        store.saveCollections([firstCollection, secondCollection]);

        expect(store.storedCollections).toEqual({ "1": firstCollection, "2": secondCollection });
    });

    it("saveCollections ignores non-collection history entries", () => {
        const collection = getFakeCollectionSummary({ id: "1" });
        const dataset: HistoryContentItemBase = { id: "ds-1", history_content_type: "dataset" };
        const store = useDatasetCollectionStore();

        store.saveCollections([collection, dataset]);

        expect(store.storedCollections).toEqual({ "1": collection });
    });

    it("getCollection returns summary without triggering a fetch when cached", async () => {
        const summary = getFakeCollectionSummary({ id: "1" });
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
        expect(store.getCollection("1")).toEqual(mockDetailedCollection("1"));
    });

    it("getDetailedCollection upgrades a summary by fetching detail", async () => {
        const summary = getFakeCollectionSummary({ id: "1" });
        const store = useDatasetCollectionStore();
        store.saveCollection(summary);

        // The summary remains available while detail is fetched.
        expect(store.getDetailedCollection("1")).toEqual(summary);
        await flushPromises();

        expect(fetchSpy).toHaveBeenCalledTimes(1);
        expect(store.getDetailedCollection("1")).toEqual(mockDetailedCollection("1"));
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
        setupTestPinia();
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
        const otherCollection = { ...getFakeCollectionSummary({ id: "other" }), collection_id: "shared-id" };

        for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            store.getDetailedCollection("shared-id");
            await flushPromises();
            expect(elementsStore.isLoadingCollectionElements(otherCollection)).toBe(false);
            await vi.advanceTimersByTimeAsync(RETRY_BACKOFF_CAP_MS);
        }
        expect(elementsStore.getLoadingCollectionElementsError(otherCollection)).toBe(false);
    });
});

function mockDetailedCollection(id: string): HDCADetailed {
    return {
        ...getFakeCollectionSummary({ id }),
        elements: [],
    };
}
