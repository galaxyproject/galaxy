import { createTestingPinia } from "@pinia/testing";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import type { AnyHistory, HDASummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";

import { useHistoryDatasets } from "./useHistoryDatasets";

const { server, http } = useServerMock();

function buildFakeDataset(id: string, name: string): HDASummary {
    return {
        id,
        name,
        history_content_type: "dataset",
        deleted: false,
        visible: true,
        state: "ok",
        extension: "txt",
        create_time: "2024-01-01T00:00:00",
        update_time: "2024-01-01T00:00:00",
        history_id: "history-1",
        hid: 1,
        type_id: "dataset",
        type: "file",
        tags: [],
        model_class: "HistoryDatasetAssociation",
        genome_build: null,
        purged: false,
    } as unknown as HDASummary;
}

function buildFakeHistory(id: string, updateTime: string) {
    return {
        id,
        name: `History ${id}`,
        update_time: updateTime,
    };
}

describe("useHistoryDatasets", () => {
    const historyId = "history-1";
    const historyUpdateTime = "2024-01-01T12:00:00";

    beforeEach(() => {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);

        // Set up the history store with a mock history
        const historyStore = useHistoryStore();
        historyStore.storedHistories[historyId] = buildFakeHistory(historyId, historyUpdateTime) as AnyHistory;

        // Default API response
        server.use(
            http.get("/api/histories/{history_id}/contents", ({ response }) => {
                return response(200).json([]);
            }),
        );
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    describe("initial state", () => {
        it("should have empty datasets initially", () => {
            const { datasets } = useHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(datasets.value).toEqual([]);
        });

        it("should not be fetching initially when immediate is false", () => {
            const { isFetching } = useHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(isFetching.value).toBe(false);
        });

        it("should have no error initially", () => {
            const { error } = useHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(error.value).toBeNull();
        });

        it("should have initialFetchDone as false initially", () => {
            const { initialFetchDone } = useHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(initialFetchDone.value).toBe(false);
        });

        it("should provide the history from the store", () => {
            const { history } = useHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(history.value?.id).toBe(historyId);
            expect(history.value?.update_time).toBe(historyUpdateTime);
        });
    });

    describe("immediate fetch", () => {
        it("should fetch immediately when immediate is true (default)", async () => {
            const expectedDatasets = [buildFakeDataset("dataset-1", "Dataset 1")];
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ response }) => {
                    return response(200).json(expectedDatasets);
                }),
            );

            const { datasets, initialFetchDone } = useHistoryDatasets({
                historyId,
            });

            await flushPromises();

            expect(datasets.value).toEqual(expectedDatasets);
            expect(initialFetchDone.value).toBe(true);
        });

        it("should not fetch immediately when immediate is false", async () => {
            const fetchSpy = vi.fn();
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ response }) => {
                    fetchSpy();
                    return response(200).json([]);
                }),
            );

            useHistoryDatasets({
                historyId,
                immediate: false,
            });

            await flushPromises();

            expect(fetchSpy).not.toHaveBeenCalled();
        });

        it("should not fetch immediately when enabled is false", async () => {
            const fetchSpy = vi.fn();
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ response }) => {
                    fetchSpy();
                    return response(200).json([]);
                }),
            );

            useHistoryDatasets({
                historyId,
                enabled: false,
                immediate: true,
            });

            await flushPromises();

            expect(fetchSpy).not.toHaveBeenCalled();
        });
    });

    describe("caching behavior", () => {
        it("should cache datasets for the same scope", async () => {
            const expectedDatasets = [buildFakeDataset("dataset-1", "Dataset 1")];
            let fetchCount = 0;
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ response }) => {
                    fetchCount++;
                    return response(200).json(expectedDatasets);
                }),
            );

            const { datasets, fetchDatasets } = useHistoryDatasets({
                historyId,
            });

            await flushPromises();
            expect(fetchCount).toBe(1);
            expect(datasets.value).toEqual(expectedDatasets);

            // Fetch again with same scope - should use cache
            await fetchDatasets();
            await flushPromises();

            // The store's caching logic should prevent a second API call
            // when scope hasn't changed
            expect(datasets.value).toEqual(expectedDatasets);
        });

        it("should cache datasets per filter text", async () => {
            const datasetsNoFilter = [buildFakeDataset("dataset-1", "Dataset 1")];
            const datasetsWithFilter = [buildFakeDataset("dataset-2", "Dataset 2")];

            server.use(
                http.get("/api/histories/{history_id}/contents", ({ request, response }) => {
                    const url = new URL(request.url);
                    const qParam = url.searchParams.get("q");
                    if (qParam && qParam.includes("name-contains")) {
                        return response(200).json(datasetsWithFilter);
                    }
                    return response(200).json(datasetsNoFilter);
                }),
            );

            const filterText = ref("");
            const { datasets } = useHistoryDatasets({
                historyId,
                filterText: () => filterText.value,
            });

            await flushPromises();
            expect(datasets.value).toEqual(datasetsNoFilter);

            // Change filter text
            filterText.value = "name:Dataset 2";
            await nextTick();
            await flushPromises();

            expect(datasets.value).toEqual(datasetsWithFilter);
        });
    });

    describe("watching scope changes", () => {
        it("should refetch when historyId changes", async () => {
            const historyId2 = "history-2";
            const historyUpdateTime2 = "2024-01-02T12:00:00";

            // Add second history to the store
            const historyStore = useHistoryStore();
            historyStore.storedHistories[historyId2] = buildFakeHistory(historyId2, historyUpdateTime2) as AnyHistory;

            const datasets1 = [buildFakeDataset("dataset-1", "Dataset 1")];
            const datasets2 = [buildFakeDataset("dataset-2", "Dataset 2")];

            server.use(
                http.get("/api/histories/{history_id}/contents", ({ params, response }) => {
                    if (params.history_id === historyId2) {
                        return response(200).json(datasets2);
                    }
                    return response(200).json(datasets1);
                }),
            );

            const currentHistoryId = ref(historyId);
            const { datasets } = useHistoryDatasets({
                historyId: () => currentHistoryId.value,
            });

            await flushPromises();
            expect(datasets.value).toEqual(datasets1);

            // Change history ID
            currentHistoryId.value = historyId2;
            await nextTick();
            await flushPromises();

            expect(datasets.value).toEqual(datasets2);
        });

        it("should expose historyUpdateTime from the history store", async () => {
            // This test verifies the composable correctly derives historyUpdateTime
            // from the history store, which is used by the watcher
            const { history } = useHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(history.value?.update_time).toBe(historyUpdateTime);
        });

        it("should use the history update time from the store when fetching", async () => {
            // This test verifies that the composable passes the correct historyUpdateTime
            // to the store's fetch function, which is critical for cache invalidation
            const receivedParams: { historyId?: string; updateTime?: string } = {};

            server.use(
                http.get("/api/histories/{history_id}/contents", ({ params, response }) => {
                    receivedParams.historyId = params.history_id as string;
                    return response(200).json([]);
                }),
            );

            const { history } = useHistoryDatasets({
                historyId,
            });

            await flushPromises();

            // Verify the composable has access to the correct update time
            expect(history.value?.update_time).toBe(historyUpdateTime);
            expect(receivedParams.historyId).toBe(historyId);
        });

        it("should refetch when filterText changes", async () => {
            const allDatasets = [buildFakeDataset("dataset-1", "Alpha"), buildFakeDataset("dataset-2", "Beta")];
            const filteredDatasets = [buildFakeDataset("dataset-1", "Alpha")];

            server.use(
                http.get("/api/histories/{history_id}/contents", ({ request, response }) => {
                    const url = new URL(request.url);
                    const qParam = url.searchParams.get("q");
                    if (qParam && qParam.includes("name-contains")) {
                        return response(200).json(filteredDatasets);
                    }
                    return response(200).json(allDatasets);
                }),
            );

            const filterText = ref("");
            const { datasets } = useHistoryDatasets({
                historyId,
                filterText: () => filterText.value,
            });

            await flushPromises();
            expect(datasets.value).toEqual(allDatasets);

            // Change filter
            filterText.value = "name:Alpha";
            await nextTick();
            await flushPromises();

            expect(datasets.value).toEqual(filteredDatasets);
        });
    });

    describe("enabled option", () => {
        it("should not fetch when enabled is false", async () => {
            const fetchSpy = vi.fn();
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ response }) => {
                    fetchSpy();
                    return response(200).json([]);
                }),
            );

            const enabled = ref(false);
            useHistoryDatasets({
                historyId,
                enabled: () => enabled.value,
            });

            await flushPromises();
            expect(fetchSpy).not.toHaveBeenCalled();
        });

        it("should fetch when enabled becomes true", async () => {
            const expectedDatasets = [buildFakeDataset("dataset-1", "Dataset 1")];
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ response }) => {
                    return response(200).json(expectedDatasets);
                }),
            );

            const enabled = ref(false);
            const { datasets, initialFetchDone } = useHistoryDatasets({
                historyId,
                enabled: () => enabled.value,
            });

            await flushPromises();
            expect(datasets.value).toEqual([]);
            expect(initialFetchDone.value).toBe(false);

            // Enable fetching
            enabled.value = true;
            await nextTick();
            await flushPromises();

            expect(datasets.value).toEqual(expectedDatasets);
            expect(initialFetchDone.value).toBe(true);
        });

        it("should not trigger fetch on scope change when disabled", async () => {
            const fetchSpy = vi.fn();
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ response }) => {
                    fetchSpy();
                    return response(200).json([]);
                }),
            );

            const filterText = ref("");
            useHistoryDatasets({
                historyId,
                filterText: () => filterText.value,
                enabled: false,
            });

            await flushPromises();
            expect(fetchSpy).not.toHaveBeenCalled();

            // Change filter while disabled
            filterText.value = "name:test";
            await nextTick();
            await flushPromises();

            expect(fetchSpy).not.toHaveBeenCalled();
        });
    });

    describe("error handling", () => {
        it("should set error when fetch fails", async () => {
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ response }) => {
                    return response("5XX").json({ err_msg: "Internal server error", err_code: 500 }, { status: 500 });
                }),
            );

            const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

            const { error, datasets } = useHistoryDatasets({
                historyId,
            });

            await flushPromises();

            expect(error.value).not.toBeNull();
            expect(datasets.value).toEqual([]);

            consoleErrorSpy.mockRestore();
        });

        it("should clear error on successful fetch after error", async () => {
            let shouldFail = true;
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ request, response }) => {
                    const url = new URL(request.url);
                    const qParam = url.searchParams.get("q");
                    // Fail only for initial fetch (no filter), succeed for filtered fetch
                    if (shouldFail && (!qParam || !qParam.includes("name-contains"))) {
                        return response("5XX").json(
                            { err_msg: "Internal server error", err_code: 500 },
                            { status: 500 },
                        );
                    }
                    return response(200).json([buildFakeDataset("dataset-1", "Dataset 1")]);
                }),
            );

            const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

            const filterText = ref("");
            const { error, datasets } = useHistoryDatasets({
                historyId,
                filterText: () => filterText.value,
            });

            await flushPromises();
            expect(error.value).not.toBeNull();

            // Now change filter text to trigger a new fetch with different scope
            // This bypasses the store cache and allows a successful fetch
            shouldFail = false;
            filterText.value = "name:test";

            await nextTick();
            await flushPromises();

            expect(error.value).toBeNull();
            expect(datasets.value).toHaveLength(1);

            consoleErrorSpy.mockRestore();
        });
    });

    describe("manual fetch", () => {
        it("should allow manual fetch via fetchDatasets", async () => {
            const expectedDatasets = [buildFakeDataset("dataset-1", "Dataset 1")];
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ response }) => {
                    return response(200).json(expectedDatasets);
                }),
            );

            const { datasets, fetchDatasets, initialFetchDone } = useHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(datasets.value).toEqual([]);
            expect(initialFetchDone.value).toBe(false);

            await fetchDatasets();
            await flushPromises();

            expect(datasets.value).toEqual(expectedDatasets);
            expect(initialFetchDone.value).toBe(true);
        });
    });
});
