import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import type { HDCASummary, HistoryItemSummary } from "@/api";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";
import { useUploadDatasetMonitorStore } from "@/stores/uploadDatasetMonitorStore";

const { mockGetHistoryItems, mockFetchHistoryItems, mockStartWatching, mockStopWatching, mockWatchHandlers } =
    vi.hoisted(() => ({
        mockGetHistoryItems: vi.fn(),
        mockFetchHistoryItems: vi.fn(),
        mockStartWatching: vi.fn(),
        mockStopWatching: vi.fn(),
        mockWatchHandlers: [] as Array<() => Promise<void>>,
    }));

const mockCurrentHistoryId = ref<string | null>("hist_1");

vi.mock("@/stores/historyItemsStore", () => ({
    useHistoryItemsStore: () => ({
        getHistoryItems: mockGetHistoryItems,
        fetchHistoryItems: mockFetchHistoryItems,
    }),
}));

vi.mock("@/stores/historyStore", () => ({
    // The getter keeps the store's `currentHistoryId` watch reactive to
    // mockCurrentHistoryId changes.
    useHistoryStore: () => ({
        get currentHistoryId() {
            return mockCurrentHistoryId.value;
        },
    }),
}));

vi.mock("@/composables/resourceWatcher", () => ({
    useResourceWatcher: (handler: () => Promise<void>) => {
        mockWatchHandlers.push(handler);
        return {
            startWatchingResource: mockStartWatching,
            stopWatchingResource: mockStopWatching,
            dispose: mockStopWatching,
            isWatchingResource: ref(false),
        };
    },
}));

function makePastedItem(name = "file.txt", targetHistoryId = "hist_1"): NewUploadItem {
    return {
        uploadMode: "paste-content",
        name,
        content: "hello world",
        size: 11,
        targetHistoryId,
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        autoDecompress: true,
        deferred: false,
    };
}

function makeHistoryItem(id: string, state: string): HistoryItemSummary {
    return {
        id,
        state,
        hid: 1,
        name: id,
        history_content_type: "dataset",
        type: "file",
        extension: "txt",
        url: "",
        deleted: false,
        visible: true,
        purged: false,
        create_time: "",
        update_time: "",
        model_class: "HistoryDatasetAssociation",
        history_id: "hist_1",
        tags: [],
    } as unknown as HistoryItemSummary;
}

function makeHDCAItem(id: string, populatedState: string | null = "ok"): HDCASummary {
    return {
        id,
        hid: 1,
        name: id,
        history_content_type: "dataset_collection",
        type: "collection",
        collection_type: "list",
        populated_state: populatedState,
        elements_states: {},
        job_state_summary: {},
        deleted: false,
        visible: true,
        purged: false,
        create_time: "",
        update_time: "",
        model_class: "HistoryDatasetCollectionAssociation",
        history_id: "hist_1",
        tags: [],
        url: "",
    } as unknown as HDCASummary;
}

describe("useUploadDatasetMonitorStore", () => {
    let uploadState: ReturnType<typeof useUploadState>;
    let monitor: ReturnType<typeof useUploadDatasetMonitorStore> | undefined;

    function createMonitor() {
        monitor = useUploadDatasetMonitorStore();
    }

    beforeEach(() => {
        setActivePinia(createPinia());
        vi.clearAllMocks();
        mockWatchHandlers.length = 0;
        mockCurrentHistoryId.value = "hist_1";
        mockGetHistoryItems.mockReturnValue([]);
        mockFetchHistoryItems.mockResolvedValue(undefined);
        uploadState = useUploadState();
        uploadState.clearAll();
    });

    afterEach(() => {
        // Shared module-level upload state persists between tests.
        monitor?.$dispose();
        monitor = undefined;
    });

    it("resolves an upload when its dataset reaches ok state", () => {
        mockGetHistoryItems.mockReturnValue([makeHistoryItem("ds_1", "ok")]);

        const id = uploadState.addUploadItem(makePastedItem());
        uploadState.setStatus(id, "uploading");
        uploadState.markProcessing(id, ["ds_1"]);
        createMonitor();

        const item = uploadState.activeItems.value.find((u) => u.id === id)!;
        expect(item.status).toBe("completed");
        expect(item.datasetIds).toEqual(["ds_1"]);
    });

    it("marks an upload as error when its dataset reaches an error state", () => {
        mockGetHistoryItems.mockReturnValue([makeHistoryItem("ds_1", "error")]);

        const id = uploadState.addUploadItem(makePastedItem());
        uploadState.setStatus(id, "uploading");
        uploadState.markProcessing(id, ["ds_1"]);
        createMonitor();

        const item = uploadState.activeItems.value.find((u) => u.id === id)!;
        expect(item.status).toBe("error");
        expect(item.error).toBeTruthy();
    });

    it("updates datasetState for non-terminal states without resolving", () => {
        mockGetHistoryItems.mockReturnValue([makeHistoryItem("ds_1", "running")]);

        const id = uploadState.addUploadItem(makePastedItem());
        uploadState.setStatus(id, "uploading");
        uploadState.markProcessing(id, ["ds_1"]);
        createMonitor();

        const item = uploadState.activeItems.value.find((u) => u.id === id)!;
        expect(item.status).toBe("processing");
        expect(item.datasetState).toBe("running");
    });

    it("only starts a fallback poller for non-current histories", () => {
        mockGetHistoryItems.mockReturnValue([makeHistoryItem("ds_1", "running")]);

        const currentId = uploadState.addUploadItem(makePastedItem());
        uploadState.setStatus(currentId, "uploading");
        uploadState.markProcessing(currentId, ["ds_1"]);

        const otherId = uploadState.addUploadItem(makePastedItem("file.txt", "hist_2"));
        uploadState.setStatus(otherId, "uploading");
        uploadState.markProcessing(otherId, ["ds_1"]);
        createMonitor();

        expect(mockStartWatching).toHaveBeenCalledTimes(1);
    });

    it("leaves upload pending when dataset is not yet in history items", () => {
        mockGetHistoryItems.mockReturnValue([]);

        const id = uploadState.addUploadItem(makePastedItem());
        uploadState.setStatus(id, "uploading");
        uploadState.markProcessing(id, ["ds_1"]);
        createMonitor();

        const item = uploadState.activeItems.value.find((u) => u.id === id)!;
        expect(item.status).toBe("processing");
    });

    it("does not monitor a cancelled upload", () => {
        mockGetHistoryItems.mockReturnValue([makeHistoryItem("ds_1", "ok")]);

        const id = uploadState.addUploadItem(makePastedItem());
        uploadState.setStatus(id, "uploading");
        uploadState.cancelUpload(id);
        createMonitor();

        const item = uploadState.activeItems.value.find((u) => u.id === id)!;
        expect(item.status).toBe("cancelled");
    });

    describe("reactive registration", () => {
        it("registers and resolves an upload that enters processing after store creation", async () => {
            mockGetHistoryItems.mockReturnValue([makeHistoryItem("ds_1", "ok")]);

            createMonitor();

            const id = uploadState.addUploadItem(makePastedItem());
            uploadState.setStatus(id, "uploading");
            uploadState.markProcessing(id, ["ds_1"]);
            await nextTick();

            const item = uploadState.activeItems.value.find((u) => u.id === id)!;
            expect(item.status).toBe("completed");
        });

        it("registers and resolves a batch that enters processing after store creation", async () => {
            mockGetHistoryItems.mockReturnValue([makeHDCAItem("hdca_1", "ok")]);

            createMonitor();

            const batchId = uploadState.addBatch(
                { name: "Test Collection", type: "list", hideSourceItems: false, historyId: "hist_1" },
                [],
            );
            uploadState.updateBatchStatus(batchId, "processing");
            uploadState.setBatchCollectionId(batchId, "hdca_1");
            await nextTick();

            expect(uploadState.getBatch(batchId)?.status).toBe("completed");
        });

        it("defers the fallback poller until the current history is loaded", async () => {
            mockCurrentHistoryId.value = null;
            mockGetHistoryItems.mockReturnValue([makeHistoryItem("ds_1", "running")]);

            const id = uploadState.addUploadItem(makePastedItem("file.txt", "hist_2"));
            uploadState.setStatus(id, "uploading");
            uploadState.markProcessing(id, ["ds_1"]);
            createMonitor();

            await nextTick();
            expect(mockStartWatching).not.toHaveBeenCalled();

            mockCurrentHistoryId.value = "hist_1";
            await nextTick();
            expect(mockStartWatching).toHaveBeenCalledTimes(1);
        });
    });

    describe("collection monitoring", () => {
        function setupCollectionBatch() {
            const batchId = uploadState.addBatch(
                { name: "Test Collection", type: "list", hideSourceItems: false, historyId: "hist_1" },
                [],
            );
            uploadState.updateBatchStatus(batchId, "processing");
            uploadState.setBatchCollectionId(batchId, "hdca_1");
            return batchId;
        }

        it("resolves a batch when the HDCA reaches ok state", () => {
            mockGetHistoryItems.mockReturnValue([makeHDCAItem("hdca_1", "ok")]);

            const batchId = setupCollectionBatch();
            createMonitor();

            expect(uploadState.getBatch(batchId)?.status).toBe("completed");
        });

        it("marks a batch as error when the HDCA has failed_populated_state", () => {
            mockGetHistoryItems.mockReturnValue([makeHDCAItem("hdca_1", "failed")]);

            const batchId = setupCollectionBatch();
            createMonitor();

            expect(uploadState.getBatch(batchId)?.status).toBe("error");
            expect(uploadState.getBatch(batchId)?.error).toBeTruthy();
        });

        it("leaves batch in processing when HDCA is still populating", () => {
            mockGetHistoryItems.mockReturnValue([makeHDCAItem("hdca_1", "new")]);

            const batchId = setupCollectionBatch();
            createMonitor();

            expect(uploadState.getBatch(batchId)?.status).toBe("processing");
        });

        it("leaves batch in processing when HDCA is not yet in history items", () => {
            mockGetHistoryItems.mockReturnValue([]);

            const batchId = setupCollectionBatch();
            createMonitor();

            expect(uploadState.getBatch(batchId)?.status).toBe("processing");
        });

        it("does not override a cancelled batch", () => {
            mockGetHistoryItems.mockReturnValue([makeHDCAItem("hdca_1", "ok")]);

            const batchId = setupCollectionBatch();
            uploadState.updateBatchStatus(batchId, "cancelled");
            createMonitor();

            expect(uploadState.getBatch(batchId)?.status).toBe("cancelled");
        });
    });

    describe("hidden and missing contents", () => {
        it("reads history items without the visible/deleted defaults", () => {
            mockGetHistoryItems.mockReturnValue([makeHistoryItem("ds_1", "ok")]);

            const id = uploadState.addUploadItem(makePastedItem());
            uploadState.setStatus(id, "uploading");
            uploadState.markProcessing(id, ["ds_1"]);
            createMonitor();

            expect(mockGetHistoryItems).toHaveBeenCalledWith("hist_1", "deleted:any visible:any");
        });

        it("fetches non-current histories without the visible/deleted defaults", async () => {
            mockGetHistoryItems.mockReturnValue([makeHistoryItem("ds_1", "running")]);

            const otherId = uploadState.addUploadItem(makePastedItem("file.txt", "hist_2"));
            uploadState.setStatus(otherId, "uploading");
            uploadState.markProcessing(otherId, ["ds_1"]);
            createMonitor();
            await nextTick();

            expect(mockWatchHandlers).toHaveLength(1);
            await mockWatchHandlers[0]?.();
            expect(mockFetchHistoryItems).toHaveBeenCalledWith("hist_2", "deleted:any visible:any", 0);
        });

        it("resolves a hidden dataset instead of hanging in processing", () => {
            mockGetHistoryItems.mockImplementation((historyId: string, filterText: string) =>
                filterText === "" ? [] : [makeHistoryItem("ds_1", "ok")],
            );

            const id = uploadState.addUploadItem(makePastedItem());
            uploadState.setStatus(id, "uploading");
            uploadState.markProcessing(id, ["ds_1"]);
            createMonitor();

            const item = uploadState.activeItems.value.find((u) => u.id === id)!;
            expect(item.status).toBe("completed");
        });

        it("marks an upload as error after missing contents exceed the timeout", async () => {
            vi.useFakeTimers();
            try {
                mockGetHistoryItems.mockReturnValue([]);

                const id = uploadState.addUploadItem(makePastedItem());
                uploadState.setStatus(id, "uploading");
                uploadState.markProcessing(id, ["ds_1"]);
                createMonitor();

                expect(uploadState.activeItems.value.find((u) => u.id === id)?.status).toBe("processing");

                await vi.advanceTimersByTimeAsync(31 * 60 * 1000);
                await nextTick();

                const item = uploadState.activeItems.value.find((u) => u.id === id)!;
                expect(item.status).toBe("error");
                expect(item.error).toBeTruthy();
            } finally {
                vi.useRealTimers();
            }
        });
    });
});
