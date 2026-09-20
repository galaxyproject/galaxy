import { suppressExpectedErrorMessages } from "@tests/vitest/helpers";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { UploadCollectionConfig } from "@/composables/upload/collectionTypes";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";

import { useUploadState } from "./uploadState";

// useUserLocalStorage is auto-mocked globally (returns a plain ref) — see tests/vitest/setup.ts
// The module-level singleton refs persist between tests, so we call clearAll() in beforeEach.

function makePastedItem(name = "file.txt", content = "hello world"): NewUploadItem {
    return {
        uploadMode: "paste-content",
        name,
        content,
        size: content.length,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        autoDecompress: true,
        deferred: false,
    };
}

const BATCH_CONFIG: UploadCollectionConfig = {
    name: "My Collection",
    type: "list",
    hideSourceItems: false,
    historyId: "hist_1",
};

describe("useUploadState", () => {
    let state: ReturnType<typeof useUploadState>;

    beforeEach(() => {
        state = useUploadState();
        state.clearAll();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("initial state", () => {
        it("has no uploads and all counters at zero", () => {
            expect(state.activeItems.value).toHaveLength(0);
            expect(state.activeBatches.value).toHaveLength(0);
            expect(state.hasUploads.value).toBe(false);
            expect(state.isUploading.value).toBe(false);
            expect(state.hasCompleted.value).toBe(false);
            expect(state.uploadingCount.value).toBe(0);
            expect(state.completedCount.value).toBe(0);
            expect(state.errorCount.value).toBe(0);
            expect(state.totalProgress.value).toBe(0);
            expect(state.orderedUploadItems.value).toHaveLength(0);
        });
    });

    describe("addUploadItem", () => {
        it("returns a unique ID and adds item to activeItems", () => {
            const id = state.addUploadItem(makePastedItem());

            expect(id).toBeTruthy();
            expect(state.activeItems.value).toHaveLength(1);
            expect(state.hasUploads.value).toBe(true);
        });

        it("initializes item with queued status, zero progress, and correct name", () => {
            const id = state.addUploadItem(makePastedItem("report.txt", "content"));

            const item = state.activeItems.value.find((i) => i.id === id);
            expect(item?.status).toBe("queued");
            expect(item?.progress).toBe(0);
            expect(item?.name).toBe("report.txt");
        });

        it("standalone item appears in standaloneUploads and orderedUploadItems", () => {
            const id = state.addUploadItem(makePastedItem());

            expect(state.standaloneUploads.value.map((i) => i.id)).toContain(id);
            expect(state.orderedUploadItems.value).toHaveLength(1);
            expect(state.orderedUploadItems.value[0]?.type).toBe("upload");
        });

        it("item associated with a batchId does not appear in standaloneUploads", () => {
            const batchId = state.addBatch(BATCH_CONFIG, []);
            const id = state.addUploadItem(makePastedItem(), batchId);

            const item = state.activeItems.value.find((i) => i.id === id);
            expect(item?.batchId).toBe(batchId);
            expect(state.standaloneUploads.value.map((i) => i.id)).not.toContain(id);
        });
    });

    describe("addBatch", () => {
        it("creates a batch with uploading status, the provided upload IDs, and no collectionId", () => {
            const id1 = state.addUploadItem(makePastedItem("a.txt"));
            const id2 = state.addUploadItem(makePastedItem("b.txt"));

            const batchId = state.addBatch(BATCH_CONFIG, [id1, id2]);

            const batch = state.getBatch(batchId);
            expect(batch?.status).toBe("uploading");
            expect(batch?.uploadIds).toEqual([id1, id2]);
            expect(batch?.datasetIds).toEqual([]);
            expect(batch?.collectionId).toBeUndefined();
        });

        it("batch appears in batchesWithProgress with aggregated upload data", () => {
            const id = state.addUploadItem(makePastedItem());
            const batchId = state.addBatch(BATCH_CONFIG, [id]);

            const bwp = state.batchesWithProgress.value.find((b) => b.id === batchId);
            expect(bwp?.uploads).toHaveLength(1);
            expect(bwp?.progress).toBe(0);
            expect(bwp?.allCompleted).toBe(false);
            expect(bwp?.hasError).toBe(false);
        });
    });

    describe("computed counts", () => {
        it("tallies uploading, completed, and errored items independently", () => {
            const uploadingId = state.addUploadItem(makePastedItem("uploading.txt"));
            const completedId = state.addUploadItem(makePastedItem("done.txt"));
            const erroredId = state.addUploadItem(makePastedItem("failed.txt"));

            state.setStatus(uploadingId, "uploading");
            state.setStatus(completedId, "completed");
            state.setError(erroredId, "network error");

            expect(state.uploadingCount.value).toBe(1);
            expect(state.completedCount.value).toBe(1);
            expect(state.errorCount.value).toBe(1);
            expect(state.isUploading.value).toBe(true);
            expect(state.hasCompleted.value).toBe(true);
        });

        it("isUploading is false when no items are in uploading or processing state", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "completed");

            expect(state.isUploading.value).toBe(false);
        });

        it("uploadingCount and isUploading include processing items", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "uploading");
            state.markProcessing(id, ["ds_1"]);

            expect(state.uploadingCount.value).toBe(1);
            expect(state.isUploading.value).toBe(true);
            expect(state.completedCount.value).toBe(0);
        });
    });

    describe("progress tracking", () => {
        it("updateProgress updates the item's progress value", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "uploading");
            state.updateProgress(id, 50);

            const item = state.activeItems.value.find((i) => i.id === id)!;
            expect(item.progress).toBe(50);
        });

        it("reaching 100% does not auto-transition item status", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "uploading");
            state.updateProgress(id, 100);

            const item = state.activeItems.value.find((i) => i.id === id)!;
            expect(item.progress).toBe(100);
            expect(item.status).toBe("uploading");
        });

        it("cancellation is terminal and cannot be overridden by lifecycle actions", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "uploading");
            state.cancelUpload(id);

            state.markProcessing(id, ["ds_1"]);
            state.markDatasetsResolved(id);
            state.markDatasetsFailed(id, "error message");
            state.setStatus(id, "uploading");
            state.setError(id, "error message");

            const item = state.activeItems.value.find((i) => i.id === id)!;
            expect(item.status).toBe("cancelled");
            expect(item.datasetIds).toEqual([]);
        });

        it("totalProgress is the average progress across all items", () => {
            const id1 = state.addUploadItem(makePastedItem("a.txt"));
            const id2 = state.addUploadItem(makePastedItem("b.txt"));
            state.updateProgress(id1, 40);
            state.updateProgress(id2, 60);

            expect(state.totalProgress.value).toBe(50);
        });

        it("totalSizeBytes sums item sizes and uploadedSizeBytes reflects partial progress", () => {
            // makePastedItem uses content.length as size: "hello" = 5, "world!" = 6
            const id1 = state.addUploadItem(makePastedItem("a.txt", "hello"));
            const id2 = state.addUploadItem(makePastedItem("b.txt", "world!"));
            state.updateProgress(id1, 100);
            state.updateProgress(id2, 0);

            expect(state.totalSizeBytes.value).toBe(11);
            expect(state.uploadedSizeBytes.value).toBe(5); // only id1 is fully uploaded
        });
    });

    describe("batch lifecycle", () => {
        function setupBatch() {
            const id1 = state.addUploadItem(makePastedItem("a.txt"));
            const id2 = state.addUploadItem(makePastedItem("b.txt"));
            const batchId = state.addBatch(BATCH_CONFIG, [id1, id2]);
            return { id1, id2, batchId };
        }

        it("updateBatchStatus transitions the batch through status stages", () => {
            const { batchId } = setupBatch();

            state.updateBatchStatus(batchId, "creating-collection");
            expect(state.getBatch(batchId)?.status).toBe("creating-collection");

            state.updateBatchStatus(batchId, "completed");
            expect(state.getBatch(batchId)?.status).toBe("completed");
        });

        it("setBatchCollectionId stores the created collection ID on the batch", () => {
            const { batchId } = setupBatch();
            state.setBatchCollectionId(batchId, "col_abc");
            expect(state.getBatch(batchId)?.collectionId).toBe("col_abc");
        });

        it("addBatchDatasetId accumulates dataset IDs in order", () => {
            const { batchId } = setupBatch();
            state.addBatchDatasetId(batchId, "ds_1");
            state.addBatchDatasetId(batchId, "ds_2");
            expect(state.getBatch(batchId)?.datasetIds).toEqual(["ds_1", "ds_2"]);
        });

        it("batchesWithProgress.allCompleted is true when all uploads reach 100%", () => {
            const { id1, id2, batchId } = setupBatch();
            state.setStatus(id1, "uploading");
            state.setStatus(id2, "uploading");
            state.setStatus(id1, "completed");
            state.setStatus(id2, "completed");

            const bwp = state.batchesWithProgress.value.find((b) => b.id === batchId)!;
            expect(bwp.allCompleted).toBe(true);
        });

        it("batchesWithProgress.hasError is true when any upload fails", () => {
            const { id1, batchId } = setupBatch();
            state.setError(id1, "upload error");

            const bwp = state.batchesWithProgress.value.find((b) => b.id === batchId)!;
            expect(bwp.hasError).toBe(true);
        });
    });

    describe("error handling", () => {
        it("setError marks the item with error status and stores the message", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setError(id, "network failure");

            const item = state.activeItems.value.find((i) => i.id === id)!;
            expect(item.status).toBe("error");
            expect(item.error).toBe("network failure");
        });

        it("setBatchError marks the batch with error status and stores the message", () => {
            const expectedMessage = "collection creation failed";
            suppressExpectedErrorMessages([expectedMessage]);

            const batchId = state.addBatch(BATCH_CONFIG, []);
            state.setBatchError(batchId, expectedMessage);

            const batch = state.getBatch(batchId)!;
            expect(batch.status).toBe("error");
            expect(batch.error).toBe(expectedMessage);
        });
    });

    describe("clearCompleted", () => {
        it("removes completed items while preserving uploading and errored items", () => {
            const uploadingId = state.addUploadItem(makePastedItem("active.txt"));
            const completedId = state.addUploadItem(makePastedItem("done.txt"));
            const erroredId = state.addUploadItem(makePastedItem("failed.txt"));

            state.setStatus(uploadingId, "uploading");
            state.setStatus(completedId, "completed");
            state.setError(erroredId, "oops");

            state.clearCompleted();

            const remainingIds = state.activeItems.value.map((i) => i.id);
            expect(remainingIds).toContain(uploadingId);
            expect(remainingIds).toContain(erroredId);
            expect(remainingIds).not.toContain(completedId);
        });

        it("removes a completed batch after all its items are cleared", () => {
            const id1 = state.addUploadItem(makePastedItem("a.txt"));
            const id2 = state.addUploadItem(makePastedItem("b.txt"));
            const batchId = state.addBatch(BATCH_CONFIG, [id1, id2]);
            state.updateBatchStatus(batchId, "completed");
            state.setStatus(id1, "completed");
            state.setStatus(id2, "completed");

            state.clearCompleted();

            expect(state.activeBatches.value.find((b) => b.id === batchId)).toBeUndefined();
        });

        it("keeps a batch with at least one non-completed item after clearing", () => {
            const completedId = state.addUploadItem(makePastedItem("done.txt"));
            const uploadingId = state.addUploadItem(makePastedItem("active.txt"));
            const batchId = state.addBatch(BATCH_CONFIG, [completedId, uploadingId]);
            state.setStatus(completedId, "completed");
            state.setStatus(uploadingId, "uploading");

            state.clearCompleted();

            // Batch stays because uploadingId is still active
            expect(state.activeBatches.value.find((b) => b.id === batchId)).toBeDefined();
            // But the completed item is gone
            expect(state.activeItems.value.find((i) => i.id === completedId)).toBeUndefined();
        });
    });

    describe("dataset lifecycle actions", () => {
        it("markProcessing sets status to processing, progress to 100, and stores datasetIds", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "uploading");
            state.markProcessing(id, ["ds_1", "ds_2"]);

            const item = state.activeItems.value.find((i) => i.id === id)!;
            expect(item.status).toBe("processing");
            expect(item.progress).toBe(100);
            expect(item.datasetIds).toEqual(["ds_1", "ds_2"]);
        });

        it("markDatasetsResolved sets status to completed", () => {
            const id = state.addUploadItem(makePastedItem());
            state.markProcessing(id, ["ds_1"]);
            state.markDatasetsResolved(id);

            const item = state.activeItems.value.find((i) => i.id === id)!;
            expect(item.status).toBe("completed");
        });

        it("markDatasetsFailed sets status to error and stores the message", () => {
            const id = state.addUploadItem(makePastedItem());
            state.markProcessing(id, ["ds_1"]);
            state.markDatasetsFailed(id, "Metadata generation failed. Please retry.");

            const item = state.activeItems.value.find((i) => i.id === id)!;
            expect(item.status).toBe("error");
            expect(item.error).toBe("Metadata generation failed. Please retry.");
        });

        it("updateDatasetState sets datasetState without changing status", () => {
            const id = state.addUploadItem(makePastedItem());
            state.markProcessing(id, ["ds_1"]);
            state.updateDatasetState(id, "running");

            const item = state.activeItems.value.find((i) => i.id === id)!;
            expect(item.status).toBe("processing");
            expect(item.datasetState).toBe("running");
        });

        it("updateProgress only changes numeric progress while queued or uploading", () => {
            const uploadingId = state.addUploadItem(makePastedItem("uploading.txt"));
            state.setStatus(uploadingId, "uploading");
            state.updateProgress(uploadingId, 50);

            const uploadingItem = state.activeItems.value.find((i) => i.id === uploadingId)!;
            expect(uploadingItem.progress).toBe(50);
            expect(uploadingItem.status).toBe("uploading");

            const processingId = state.addUploadItem(makePastedItem("processing.txt"));
            state.markProcessing(processingId, ["ds_1"]);
            state.updateProgress(processingId, 100);

            const processingItem = state.activeItems.value.find((i) => i.id === processingId)!;
            expect(processingItem.status).toBe("processing");
            expect(processingItem.progress).toBe(100);
        });
    });

    describe("clearAll", () => {
        it("empties all items, batches, and resets computed flags", () => {
            state.addUploadItem(makePastedItem());
            state.addBatch(BATCH_CONFIG, []);

            state.clearAll();

            expect(state.activeItems.value).toHaveLength(0);
            expect(state.activeBatches.value).toHaveLength(0);
            expect(state.hasUploads.value).toBe(false);
        });
    });

    describe("cancelBatch", () => {
        it("cancels queued/uploading items while the batch is still uploading, leaving processing items alone", () => {
            const id1 = state.addUploadItem(makePastedItem("a.txt"));
            const id2 = state.addUploadItem(makePastedItem("b.txt"));
            const id3 = state.addUploadItem(makePastedItem("c.txt"));
            const batchId = state.addBatch(BATCH_CONFIG, [id1, id2, id3]);

            state.updateBatchStatus(batchId, "uploading");
            state.setStatus(id1, "uploading");
            state.setStatus(id2, "queued");
            state.markProcessing(id3, ["ds_3"]);

            state.cancelBatch(batchId);

            expect(state.activeItems.value.find((i) => i.id === id1)?.status).toBe("cancelled");
            expect(state.activeItems.value.find((i) => i.id === id2)?.status).toBe("cancelled");
            // The server already owns processing items; cancelling the batch cannot stop them.
            expect(state.activeItems.value.find((i) => i.id === id3)?.status).toBe("processing");
            expect(state.getBatch(batchId)?.status).toBe("cancelled");
        });

        it("does not cancel items that are already terminal", () => {
            const id1 = state.addUploadItem(makePastedItem("a.txt"));
            const id2 = state.addUploadItem(makePastedItem("b.txt"));
            const batchId = state.addBatch(BATCH_CONFIG, [id1, id2]);

            state.updateBatchStatus(batchId, "uploading");
            state.setStatus(id1, "completed");
            state.setError(id2, "fail");

            state.cancelBatch(batchId);

            expect(state.activeItems.value.find((i) => i.id === id1)?.status).toBe("completed");
            expect(state.activeItems.value.find((i) => i.id === id2)?.status).toBe("error");
            expect(state.getBatch(batchId)?.status).toBe("cancelled");
        });

        it("is a no-op when the batch is already processing", () => {
            const id1 = state.addUploadItem(makePastedItem("a.txt"));
            const id2 = state.addUploadItem(makePastedItem("b.txt"));
            const batchId = state.addBatch(BATCH_CONFIG, [id1, id2]);

            state.updateBatchStatus(batchId, "processing");
            state.setStatus(id1, "uploading");
            state.markProcessing(id2, ["ds_2"]);

            state.cancelBatch(batchId);

            expect(state.getBatch(batchId)?.status).toBe("processing");
            expect(state.activeItems.value.find((i) => i.id === id1)?.status).toBe("uploading");
            expect(state.activeItems.value.find((i) => i.id === id2)?.status).toBe("processing");
        });
    });

    describe("cancelAll", () => {
        it("keeps standalone items in processing status unchanged while cancelling uploading ones", () => {
            const id1 = state.addUploadItem(makePastedItem("a.txt"));
            const id2 = state.addUploadItem(makePastedItem("b.txt"));

            state.setStatus(id1, "uploading");
            state.markProcessing(id2, ["ds_2"]);

            state.cancelAll();

            expect(state.activeItems.value.find((i) => i.id === id1)?.status).toBe("cancelled");
            expect(state.activeItems.value.find((i) => i.id === id2)?.status).toBe("processing");
        });

        it("leaves fully-transferred (progress 100) uploads alone so the pending response can resolve them", () => {
            const transferringId = state.addUploadItem(makePastedItem("active.txt"));
            const transferredId = state.addUploadItem(makePastedItem("done-bytes.txt"));

            state.setStatus(transferringId, "uploading");
            state.updateProgress(transferringId, 40);
            state.setStatus(transferredId, "uploading");
            state.updateProgress(transferredId, 100);

            state.cancelAll();

            expect(state.activeItems.value.find((i) => i.id === transferringId)?.status).toBe("cancelled");
            expect(state.activeItems.value.find((i) => i.id === transferredId)?.status).toBe("uploading");
            expect(state.hasActiveUploads.value).toBe(false);
        });

        it("keeps batches already in processing status unchanged", () => {
            const batchId = state.addBatch(BATCH_CONFIG, []);
            state.updateBatchStatus(batchId, "processing");

            state.cancelAll();

            expect(state.getBatch(batchId)?.status).toBe("processing");
        });

        it("cancels an uploading batch via cancelAll", () => {
            const id1 = state.addUploadItem(makePastedItem("a.txt"));
            const batchId = state.addBatch(BATCH_CONFIG, [id1]);

            state.updateBatchStatus(batchId, "uploading");
            state.setStatus(id1, "uploading");

            state.cancelAll();

            expect(state.activeItems.value.find((i) => i.id === id1)?.status).toBe("cancelled");
            expect(state.getBatch(batchId)?.status).toBe("cancelled");
        });
    });

    describe("resolveBatch", () => {
        function setupProcessingBatch() {
            const id1 = state.addUploadItem(makePastedItem("a.txt"));
            const id2 = state.addUploadItem(makePastedItem("b.txt"));
            const id3 = state.addUploadItem(makePastedItem("c.txt"));
            const batchId = state.addBatch(BATCH_CONFIG, [id1, id2, id3]);

            state.setStatus(id1, "processing");
            state.setStatus(id2, "processing");
            state.setStatus(id3, "cancelled");
            return { id1, id2, id3, batchId };
        }

        it("markBatchResolved completes processing items and preserves cancelled ones", () => {
            const { id1, id2, id3, batchId } = setupProcessingBatch();

            state.markBatchResolved(batchId);

            expect(state.activeItems.value.find((i) => i.id === id1)?.status).toBe("completed");
            expect(state.activeItems.value.find((i) => i.id === id2)?.status).toBe("completed");
            expect(state.activeItems.value.find((i) => i.id === id3)?.status).toBe("cancelled");
            expect(state.getBatch(batchId)?.status).toBe("completed");
        });

        it("markBatchFailed errors processing items and preserves cancelled ones", () => {
            const { id1, id2, id3, batchId } = setupProcessingBatch();

            state.markBatchFailed(batchId, "Collection failed to populate");

            expect(state.activeItems.value.find((i) => i.id === id1)?.status).toBe("error");
            expect(state.activeItems.value.find((i) => i.id === id1)?.error).toBe("Collection failed to populate");
            expect(state.activeItems.value.find((i) => i.id === id2)?.status).toBe("error");
            expect(state.activeItems.value.find((i) => i.id === id3)?.status).toBe("cancelled");
            expect(state.getBatch(batchId)?.status).toBe("error");
            expect(state.getBatch(batchId)?.error).toBe("Collection failed to populate");
        });
    });

    describe("dismiss", () => {
        it("dismissUpload removes an errored item", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setError(id, "oops");

            state.dismissUpload(id);

            expect(state.activeItems.value.find((i) => i.id === id)).toBeUndefined();
        });

        it("dismissUpload leaves non-error items alone", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "uploading");

            state.dismissUpload(id);

            expect(state.activeItems.value.find((i) => i.id === id)).toBeDefined();
        });

        it("dismissBatch removes an errored batch and its items", () => {
            suppressExpectedErrorMessages(["failed"]);

            const id = state.addUploadItem(makePastedItem("a.txt"));
            const batchId = state.addBatch(BATCH_CONFIG, [id]);
            state.setBatchError(batchId, "failed");

            state.dismissBatch(batchId);

            expect(state.getBatch(batchId)).toBeUndefined();
            expect(state.activeItems.value.find((i) => i.id === id)).toBeUndefined();
        });
    });
});
