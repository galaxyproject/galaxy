import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HDASummary } from "@/api";
import { loadDatasets, type LoadDatasetsResult } from "@/api/datasets";

import { useDatasetListStore } from "./datasetListStore";

vi.mock("@/api/datasets");

const mockLoadDatasets = vi.mocked(loadDatasets);

function mockSummary(id: string, name = `dataset ${id}`): HDASummary {
    return {
        id,
        name,
        history_content_type: "dataset",
        hid: 1,
        history_id: "h1",
        deleted: false,
        visible: true,
        state: "ok",
        update_time: "2026-08-01T10:00:00.000Z",
        create_time: "2026-08-01T10:00:00.000Z",
    } as HDASummary;
}

function mockResult(data: HDASummary[], totalMatches = data.length): LoadDatasetsResult {
    return { data, totalMatches };
}

describe("useDatasetListStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        mockLoadDatasets.mockReset();
    });

    it("fetches the latest datasets and caches them by id", async () => {
        mockLoadDatasets.mockResolvedValue(mockResult([mockSummary("1"), mockSummary("2")], 7));
        const store = useDatasetListStore();

        const fetched = await store.fetchDatasets({ limit: 5 });

        expect(mockLoadDatasets).toHaveBeenCalledWith({
            sortBy: "update_time",
            sortDesc: true,
            limit: 5,
            search: "",
        });
        expect(fetched).toHaveLength(2);
        expect(Object.keys(store.storedDatasets)).toEqual(["1", "2"]);
        expect(store.latestDatasetIds).toEqual(["1", "2"]);
        expect(store.latestDatasets.map((dataset) => dataset.id)).toEqual(["1", "2"]);
        expect(store.totalLatestMatches).toBe(7);
        expect(store.hasLoadedLatest).toBe(true);
        expect(store.isLoading).toBe(false);
    });

    it("merges repeated fetches into the cache without duplicating entries", async () => {
        const store = useDatasetListStore();
        mockLoadDatasets.mockResolvedValue(mockResult([mockSummary("1"), mockSummary("2")]));
        await store.fetchDatasets();

        mockLoadDatasets.mockResolvedValue(mockResult([mockSummary("2", "renamed"), mockSummary("3")]));
        await store.fetchDatasets();

        expect(Object.keys(store.storedDatasets).sort()).toEqual(["1", "2", "3"]);
        expect(store.getDatasetSummary("2")?.name).toBe("renamed");
        expect(store.latestDatasetIds).toEqual(["2", "3"]);
    });

    it("dedupes ids returned within a single response", async () => {
        mockLoadDatasets.mockResolvedValue(mockResult([mockSummary("1"), mockSummary("1")]));
        const store = useDatasetListStore();

        await store.fetchDatasets();

        expect(store.latestDatasetIds).toEqual(["1"]);
        expect(store.latestDatasets).toHaveLength(1);
    });

    it("keeps the latest list untouched for searched fetches but still caches results", async () => {
        const store = useDatasetListStore();
        mockLoadDatasets.mockResolvedValue(mockResult([mockSummary("1")], 1));
        await store.fetchDatasets();

        mockLoadDatasets.mockResolvedValue(mockResult([mockSummary("9", "needle")], 1));
        const found = await store.fetchDatasets({ search: "needle" });

        expect(mockLoadDatasets).toHaveBeenLastCalledWith({
            sortBy: "update_time",
            sortDesc: true,
            limit: 25,
            search: "needle",
        });
        expect(found.map((dataset) => dataset.id)).toEqual(["9"]);
        expect(store.latestDatasetIds).toEqual(["1"]);
        expect(store.getDatasetSummary("9")?.name).toBe("needle");
    });

    it("ensureLatestLoaded only fetches once", async () => {
        mockLoadDatasets.mockResolvedValue(mockResult([mockSummary("1")]));
        const store = useDatasetListStore();

        const first = await store.ensureLatestLoaded();
        const second = await store.ensureLatestLoaded();

        expect(mockLoadDatasets).toHaveBeenCalledTimes(1);
        expect(first.map((dataset) => dataset.id)).toEqual(["1"]);
        expect(second).toEqual(first);
    });

    it("records the error message and returns an empty list when the request fails", async () => {
        mockLoadDatasets.mockRejectedValue(new Error("boom"));
        const store = useDatasetListStore();

        const result = await store.fetchDatasets();

        expect(result).toEqual([]);
        expect(store.loadError).toBe("boom");
        expect(store.hasLoadedLatest).toBe(false);
        expect(store.isLoading).toBe(false);
    });

    it("filters the cache client-side by name", async () => {
        const store = useDatasetListStore();
        store.saveDatasets([
            mockSummary("1", "Alpha reads"),
            mockSummary("2", "Beta reads"),
            mockSummary("3", "Gamma"),
        ]);

        expect(store.searchCachedDatasets("beta").map((dataset) => dataset.id)).toEqual(["2"]);
        expect(store.searchCachedDatasets("reads")).toHaveLength(2);
        expect(store.searchCachedDatasets("", 2)).toHaveLength(2);
        expect(store.searchCachedDatasets("nope")).toEqual([]);
    });

    it("ignores entries without an id when saving", () => {
        const store = useDatasetListStore();

        store.saveDatasets([mockSummary("1"), { name: "no id" } as HDASummary]);

        expect(Object.keys(store.storedDatasets)).toEqual(["1"]);
    });
});
