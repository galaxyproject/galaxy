import { getFakeHistorySummary } from "@tests/test-data";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type EffectScope, effectScope, nextTick, ref } from "vue";

import type { HDASummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryDatasetsStore } from "@/stores/historyDatasetsStore";
import { useHistoryStore } from "@/stores/historyStore";
import { setupTestPinia } from "@/stores/testUtils";

import { useHistoryDatasets } from "./useHistoryDatasets";

const { server, http } = useServerMock();

function buildFakeDataset(id: string, name: string): HDASummary {
    return {
        id,
        dataset_id: id,
        url: `/api/histories/history-1/contents/${id}`,
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
        genome_build: null,
        purged: false,
    };
}

const scopes: EffectScope[] = [];

function createHistoryDatasets(options: Parameters<typeof useHistoryDatasets>[0]) {
    const scope = effectScope();
    scopes.push(scope);
    return scope.run(() => useHistoryDatasets(options))!;
}

function respondWithDatasets(datasets: HDASummary[]) {
    const requestSpy = vi.fn();
    server.use(
        http.get("/api/histories/{history_id}/contents", ({ params, response }) => {
            requestSpy(params.history_id);
            return response(200).json(datasets);
        }),
    );
    return requestSpy;
}

describe("useHistoryDatasets", () => {
    const historyId = "history-1";
    const historyUpdateTime = "2024-01-01T12:00:00";

    beforeEach(() => {
        setupTestPinia();

        const historyStore = useHistoryStore();
        historyStore.storedHistories[historyId] = getFakeHistorySummary({
            id: historyId,
            name: `History ${historyId}`,
            update_time: historyUpdateTime,
        });
    });

    afterEach(() => {
        scopes.splice(0).forEach((scope) => scope.stop());
        vi.restoreAllMocks();
    });

    describe("initial state", () => {
        it("starts with empty datasets before fetching", () => {
            const { datasets } = createHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(datasets.value).toEqual([]);
        });

        it("starts idle when immediate fetching is disabled", () => {
            const { isFetching } = createHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(isFetching.value).toBe(false);
        });

        it("starts without an error", () => {
            const { error } = createHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(error.value).toBeNull();
        });

        it("starts with an unfinished initial fetch", () => {
            const { initialFetchDone } = createHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(initialFetchDone.value).toBe(false);
        });

        it("provides the history from the store", () => {
            const { history } = createHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(history.value?.id).toBe(historyId);
            expect(history.value?.update_time).toBe(historyUpdateTime);
        });
    });

    describe("immediate fetch", () => {
        it("fetches immediately by default", async () => {
            const expectedDatasets = [buildFakeDataset("dataset-1", "Dataset 1")];
            respondWithDatasets(expectedDatasets);

            const { datasets, initialFetchDone } = createHistoryDatasets({
                historyId,
            });

            await flushPromises();

            expect(datasets.value).toEqual(expectedDatasets);
            expect(initialFetchDone.value).toBe(true);
        });

        it("does not fetch immediately when immediate is false", async () => {
            const fetchSpy = respondWithDatasets([]);

            createHistoryDatasets({
                historyId,
                immediate: false,
            });

            await flushPromises();

            expect(fetchSpy).not.toHaveBeenCalled();
        });

        it("does not fetch immediately when enabled is false", async () => {
            const fetchSpy = respondWithDatasets([]);

            createHistoryDatasets({
                historyId,
                enabled: false,
                immediate: true,
            });

            await flushPromises();

            expect(fetchSpy).not.toHaveBeenCalled();
        });
    });

    describe("caching behavior", () => {
        it("reuses cached datasets without requesting the same scope again", async () => {
            const expectedDatasets = [buildFakeDataset("dataset-1", "Dataset 1")];
            const requestSpy = respondWithDatasets(expectedDatasets);

            const { datasets, fetchDatasets } = createHistoryDatasets({
                historyId,
            });

            await flushPromises();
            expect(requestSpy).toHaveBeenCalledExactlyOnceWith(historyId);
            expect(datasets.value).toEqual(expectedDatasets);

            await fetchDatasets();

            expect(requestSpy).toHaveBeenCalledTimes(1);
            expect(datasets.value).toEqual(expectedDatasets);
        });

        it("switches cached results with the filter text", async () => {
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
            const { datasets } = createHistoryDatasets({
                historyId,
                filterText: () => filterText.value,
            });

            await flushPromises();
            expect(datasets.value).toEqual(datasetsNoFilter);

            filterText.value = "name:Dataset 2";
            await nextTick();
            await flushPromises();

            expect(datasets.value).toEqual(datasetsWithFilter);
        });
    });

    describe("watching scope changes", () => {
        it("refetches when the history ID changes", async () => {
            const historyId2 = "history-2";
            const historyUpdateTime2 = "2024-01-02T12:00:00";

            const historyStore = useHistoryStore();
            historyStore.storedHistories[historyId2] = getFakeHistorySummary({
                id: historyId2,
                name: `History ${historyId2}`,
                update_time: historyUpdateTime2,
            });

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
            const { datasets } = createHistoryDatasets({
                historyId: () => currentHistoryId.value,
            });

            await flushPromises();
            expect(datasets.value).toEqual(datasets1);

            currentHistoryId.value = historyId2;
            await nextTick();
            await flushPromises();

            expect(datasets.value).toEqual(datasets2);
        });

        it("exposes the stored history update time without fetching", () => {
            const { history } = createHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(history.value?.update_time).toBe(historyUpdateTime);
        });

        it("passes the stored history ID and update time to the dataset store", async () => {
            const requestSpy = respondWithDatasets([]);
            const fetchSpy = vi.spyOn(useHistoryDatasetsStore(), "fetchDatasetsForFiltertext");

            const { history } = createHistoryDatasets({
                historyId,
            });

            await flushPromises();

            expect(history.value?.update_time).toBe(historyUpdateTime);
            expect(requestSpy).toHaveBeenCalledExactlyOnceWith(historyId);
            expect(fetchSpy).toHaveBeenCalledExactlyOnceWith(historyId, historyUpdateTime, "");
        });

        it("refetches when the filter text changes", async () => {
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
            const { datasets } = createHistoryDatasets({
                historyId,
                filterText: () => filterText.value,
            });

            await flushPromises();
            expect(datasets.value).toEqual(allDatasets);

            filterText.value = "name:Alpha";
            await nextTick();
            await flushPromises();

            expect(datasets.value).toEqual(filteredDatasets);
        });
    });

    describe("enabled option", () => {
        it("does not fetch while a reactive enabled option is false", async () => {
            const fetchSpy = respondWithDatasets([]);

            const enabled = ref(false);
            createHistoryDatasets({
                historyId,
                enabled: () => enabled.value,
            });

            await flushPromises();
            expect(fetchSpy).not.toHaveBeenCalled();
        });

        it("fetches when the reactive enabled option becomes true", async () => {
            const expectedDatasets = [buildFakeDataset("dataset-1", "Dataset 1")];
            respondWithDatasets(expectedDatasets);

            const enabled = ref(false);
            const { datasets, initialFetchDone } = createHistoryDatasets({
                historyId,
                enabled: () => enabled.value,
            });

            await flushPromises();
            expect(datasets.value).toEqual([]);
            expect(initialFetchDone.value).toBe(false);

            enabled.value = true;
            await nextTick();
            await flushPromises();

            expect(datasets.value).toEqual(expectedDatasets);
            expect(initialFetchDone.value).toBe(true);
        });

        it("does not fetch after the filter changes while disabled", async () => {
            const fetchSpy = respondWithDatasets([]);

            const filterText = ref("");
            createHistoryDatasets({
                historyId,
                filterText: () => filterText.value,
                enabled: false,
            });

            await flushPromises();
            expect(fetchSpy).not.toHaveBeenCalled();

            filterText.value = "name:test";
            await nextTick();
            await flushPromises();

            expect(fetchSpy).not.toHaveBeenCalled();
        });
    });

    describe("error handling", () => {
        it("reports a failed request and retains empty datasets", async () => {
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ response }) => {
                    return response("5XX").json({ err_msg: "Internal server error", err_code: 500 }, { status: 500 });
                }),
            );

            vi.spyOn(console, "error").mockImplementation(() => {});

            const { error, datasets } = createHistoryDatasets({
                historyId,
            });

            await flushPromises();

            expect(error.value).not.toBeNull();
            expect(datasets.value).toEqual([]);
        });

        it("clears a request error after fetching a different filter successfully", async () => {
            server.use(
                http.get("/api/histories/{history_id}/contents", ({ request, response }) => {
                    const url = new URL(request.url);
                    const qParam = url.searchParams.get("q");
                    if (!qParam || !qParam.includes("name-contains")) {
                        return response("5XX").json(
                            { err_msg: "Internal server error", err_code: 500 },
                            { status: 500 },
                        );
                    }
                    return response(200).json([buildFakeDataset("dataset-1", "Dataset 1")]);
                }),
            );

            vi.spyOn(console, "error").mockImplementation(() => {});

            const filterText = ref("");
            const { error, datasets } = createHistoryDatasets({
                historyId,
                filterText: () => filterText.value,
            });

            await flushPromises();
            expect(error.value).not.toBeNull();

            filterText.value = "name:test";

            await nextTick();
            await flushPromises();

            expect(error.value).toBeNull();
            expect(datasets.value).toHaveLength(1);
        });
    });

    describe("manual fetch", () => {
        it("fetches manually when immediate fetching is disabled", async () => {
            const expectedDatasets = [buildFakeDataset("dataset-1", "Dataset 1")];
            respondWithDatasets(expectedDatasets);

            const { datasets, fetchDatasets, initialFetchDone } = createHistoryDatasets({
                historyId,
                immediate: false,
            });

            expect(datasets.value).toEqual([]);
            expect(initialFetchDone.value).toBe(false);

            await fetchDatasets();

            expect(datasets.value).toEqual(expectedDatasets);
            expect(initialFetchDone.value).toBe(true);
        });
    });
});
