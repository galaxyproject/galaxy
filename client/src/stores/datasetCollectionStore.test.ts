import { getFakeCollectionSummary } from "@tests/test-data/collections";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HDCADetailed, HistoryContentItemBase } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import { useDatasetCollectionStore } from "./datasetCollectionStore";
import { setupTestPinia } from "./testUtils";

const { server, http } = useServerMock();

const fetchSpy = vi.fn();

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

function mockDetailedCollection(id: string): HDCADetailed {
    return {
        ...getFakeCollectionSummary({ id }),
        elements: [],
    };
}
