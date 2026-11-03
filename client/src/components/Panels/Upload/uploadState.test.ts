import { suppressExpectedErrorMessages } from "@tests/vitest/helpers";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { makeCollectionConfig, makePastedItem } from "@/composables/upload/testHelpers/uploadFixtures";

import { useUploadState } from "./uploadState";

// useUserLocalStorage is auto-mocked globally (returns a plain ref) — see tests/vitest/setup.ts
// Clear the module-level singleton before and after each scenario.

describe("useUploadState", () => {
    let state: ReturnType<typeof useUploadState>;

    beforeEach(() => {
        state = useUploadState();
        state.clearAll();
    });

    afterEach(() => {
        state.clearAll();
        vi.restoreAllMocks();
    });

    function findUpload(id: string) {
        return state.activeItems.value.find((item) => item.id === id);
    }

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
        it("returns an ID and adds an active upload", () => {
            const id = state.addUploadItem(makePastedItem());

            expect(id).toBeTruthy();
            expect(state.activeItems.value).toHaveLength(1);
            expect(state.hasUploads.value).toBe(true);
        });

        it("initializes item with queued status, zero progress, and correct name", () => {
            const id = state.addUploadItem(makePastedItem({ name: "report.txt", content: "content", size: 7 }));

            expect(findUpload(id)).toMatchObject({ status: "queued", progress: 0, name: "report.txt" });
        });

        it("standalone item appears in standaloneUploads and orderedUploadItems", () => {
            const id = state.addUploadItem(makePastedItem());

            expect(state.standaloneUploads.value.map((i) => i.id)).toContain(id);
            expect(state.orderedUploadItems.value).toHaveLength(1);
            expect(state.orderedUploadItems.value[0]?.type).toBe("upload");
        });

        it("item associated with a batchId does not appear in standaloneUploads", () => {
            const batchId = state.addBatch(makeCollectionConfig(), []);
            const id = state.addUploadItem(makePastedItem(), batchId);

            expect(findUpload(id)).toMatchObject({ batchId });
            expect(state.standaloneUploads.value.map((i) => i.id)).not.toContain(id);
        });
    });

    describe("addBatch", () => {
        it("creates a batch with uploading status, the provided upload IDs, and no collectionId", () => {
            const id1 = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const id2 = state.addUploadItem(makePastedItem({ name: "b.txt" }));

            const batchId = state.addBatch(makeCollectionConfig(), [id1, id2]);

            expect(state.getBatch(batchId)).toMatchObject({
                status: "uploading",
                uploadIds: [id1, id2],
                datasetIds: [],
                collectionId: undefined,
            });
        });

        it("batch appears in batchesWithProgress with aggregated upload data", () => {
            const id = state.addUploadItem(makePastedItem());
            const batchId = state.addBatch(makeCollectionConfig(), [id]);

            const bwp = state.batchesWithProgress.value.find((b) => b.id === batchId);
            expect(bwp?.uploads).toHaveLength(1);
            expect(bwp?.progress).toBe(0);
            expect(bwp?.allCompleted).toBe(false);
            expect(bwp?.hasError).toBe(false);
        });
    });

    describe("computed counts", () => {
        it("tallies uploading, completed, and errored items independently", () => {
            const uploadingId = state.addUploadItem(makePastedItem({ name: "uploading.txt" }));
            const completedId = state.addUploadItem(makePastedItem({ name: "done.txt" }));
            const erroredId = state.addUploadItem(makePastedItem({ name: "failed.txt" }));

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

            expect(findUpload(id)).toMatchObject({ progress: 50 });
        });

        it("reaching 100% does not auto-transition item status", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "uploading");
            state.updateProgress(id, 100);

            expect(findUpload(id)).toMatchObject({ progress: 100, status: "uploading" });
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

            expect(findUpload(id)).toMatchObject({ status: "cancelled", datasetIds: [] });
        });

        it("totalProgress is the average progress across all items", () => {
            const id1 = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const id2 = state.addUploadItem(makePastedItem({ name: "b.txt" }));
            state.updateProgress(id1, 40);
            state.updateProgress(id2, 60);

            expect(state.totalProgress.value).toBe(50);
        });

        it("sums content sizes and counts only transferred bytes", () => {
            const id1 = state.addUploadItem(makePastedItem({ name: "a.txt", content: "hello", size: 5 }));
            const id2 = state.addUploadItem(makePastedItem({ name: "b.txt", content: "world!", size: 6 }));
            state.updateProgress(id1, 100);
            state.updateProgress(id2, 0);

            expect(state.totalSizeBytes.value).toBe(11);
            expect(state.uploadedSizeBytes.value).toBe(5); // only id1 is fully uploaded
        });
    });

    describe("batch lifecycle", () => {
        function setupBatch() {
            const id1 = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const id2 = state.addUploadItem(makePastedItem({ name: "b.txt" }));
            const batchId = state.addBatch(makeCollectionConfig(), [id1, id2]);
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

        it("reports allCompleted when every batch upload has completed", () => {
            const { id1, id2, batchId } = setupBatch();
            state.setStatus(id1, "uploading");
            state.setStatus(id2, "uploading");
            state.setStatus(id1, "completed");
            state.setStatus(id2, "completed");

            expect(state.batchesWithProgress.value.find((b) => b.id === batchId)).toMatchObject({ allCompleted: true });
        });

        it("batchesWithProgress.hasError is true when any upload fails", () => {
            const { id1, batchId } = setupBatch();
            state.setError(id1, "upload error");

            expect(state.batchesWithProgress.value.find((b) => b.id === batchId)).toMatchObject({ hasError: true });
        });
    });

    describe("error handling", () => {
        it("setError marks the item with error status and stores the message", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setError(id, "network failure");

            expect(findUpload(id)).toMatchObject({ status: "error", error: "network failure" });
        });

        it("setBatchError marks the batch with error status and stores the message", () => {
            const expectedMessage = "collection creation failed";
            suppressExpectedErrorMessages([expectedMessage]);

            const batchId = state.addBatch(makeCollectionConfig(), []);
            state.setBatchError(batchId, expectedMessage);

            expect(state.getBatch(batchId)).toMatchObject({ status: "error", error: expectedMessage });
        });
    });

    describe("clearCompleted", () => {
        it("removes completed items while preserving uploading and errored items", () => {
            const uploadingId = state.addUploadItem(makePastedItem({ name: "active.txt" }));
            const completedId = state.addUploadItem(makePastedItem({ name: "done.txt" }));
            const erroredId = state.addUploadItem(makePastedItem({ name: "failed.txt" }));

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
            const id1 = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const id2 = state.addUploadItem(makePastedItem({ name: "b.txt" }));
            const batchId = state.addBatch(makeCollectionConfig(), [id1, id2]);
            state.updateBatchStatus(batchId, "completed");
            state.setStatus(id1, "completed");
            state.setStatus(id2, "completed");

            state.clearCompleted();

            expect(state.activeBatches.value.find((b) => b.id === batchId)).toBeUndefined();
        });

        it("keeps a batch with at least one non-completed item after clearing", () => {
            const completedId = state.addUploadItem(makePastedItem({ name: "done.txt" }));
            const uploadingId = state.addUploadItem(makePastedItem({ name: "active.txt" }));
            const batchId = state.addBatch(makeCollectionConfig(), [completedId, uploadingId]);
            state.setStatus(completedId, "completed");
            state.setStatus(uploadingId, "uploading");

            state.clearCompleted();

            expect(state.activeBatches.value.find((b) => b.id === batchId)).toBeDefined();
            expect(findUpload(completedId)).toBeUndefined();
        });
    });

    describe("dataset lifecycle actions", () => {
        it("markProcessing sets status to processing, progress to 100, and stores datasetIds", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "uploading");
            state.markProcessing(id, ["ds_1", "ds_2"]);

            expect(findUpload(id)).toMatchObject({ status: "processing", progress: 100, datasetIds: ["ds_1", "ds_2"] });
        });

        it("markDatasetsResolved sets status to completed", () => {
            const id = state.addUploadItem(makePastedItem());
            state.markProcessing(id, ["ds_1"]);
            state.markDatasetsResolved(id);

            expect(findUpload(id)).toMatchObject({ status: "completed" });
        });

        it("markDatasetsFailed sets status to error and stores the message", () => {
            const id = state.addUploadItem(makePastedItem());
            state.markProcessing(id, ["ds_1"]);
            state.markDatasetsFailed(id, "Metadata generation failed. Please retry.");

            expect(findUpload(id)).toMatchObject({
                status: "error",
                error: "Metadata generation failed. Please retry.",
            });
        });

        it("updateDatasetState sets datasetState without changing status", () => {
            const id = state.addUploadItem(makePastedItem());
            state.markProcessing(id, ["ds_1"]);
            state.updateDatasetState(id, "running");

            expect(findUpload(id)).toMatchObject({ status: "processing", datasetState: "running" });
        });

        it("updates numeric progress while an item is uploading", () => {
            const uploadingId = state.addUploadItem(makePastedItem({ name: "uploading.txt" }));
            state.setStatus(uploadingId, "uploading");
            state.updateProgress(uploadingId, 50);

            expect(findUpload(uploadingId)).toMatchObject({ progress: 50, status: "uploading" });
        });

        it("preserves processing status and final progress when another progress event arrives", () => {
            const processingId = state.addUploadItem(makePastedItem({ name: "processing.txt" }));
            state.markProcessing(processingId, ["ds_1"]);
            state.updateProgress(processingId, 100);

            expect(findUpload(processingId)).toMatchObject({ status: "processing", progress: 100 });
        });
    });

    describe("clearAll", () => {
        it("empties all items, batches, and resets computed flags", () => {
            state.addUploadItem(makePastedItem());
            state.addBatch(makeCollectionConfig(), []);

            state.clearAll();

            expect(state.activeItems.value).toHaveLength(0);
            expect(state.activeBatches.value).toHaveLength(0);
            expect(state.hasUploads.value).toBe(false);
        });
    });

    describe("cancelBatch", () => {
        it("cancels queued/uploading items while the batch is still uploading, leaving processing items alone", () => {
            const uploadingId = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const queuedId = state.addUploadItem(makePastedItem({ name: "b.txt" }));
            const processingId = state.addUploadItem(makePastedItem({ name: "c.txt" }));
            const batchId = state.addBatch(makeCollectionConfig(), [uploadingId, queuedId, processingId]);

            state.updateBatchStatus(batchId, "uploading");
            state.setStatus(uploadingId, "uploading");
            state.setStatus(queuedId, "queued");
            state.markProcessing(processingId, ["ds_3"]);

            state.cancelBatch(batchId);

            expect(findUpload(uploadingId)).toMatchObject({ status: "cancelled" });
            expect(findUpload(queuedId)).toMatchObject({ status: "cancelled" });
            // The server already owns processing items; cancelling the batch cannot stop them.
            expect(findUpload(processingId)).toMatchObject({ status: "processing" });
            expect(state.getBatch(batchId)?.status).toBe("cancelled");
        });

        it("does not cancel items that are already terminal", () => {
            const completedId = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const erroredId = state.addUploadItem(makePastedItem({ name: "b.txt" }));
            const batchId = state.addBatch(makeCollectionConfig(), [completedId, erroredId]);

            state.updateBatchStatus(batchId, "uploading");
            state.setStatus(completedId, "completed");
            state.setError(erroredId, "fail");

            state.cancelBatch(batchId);

            expect(findUpload(completedId)).toMatchObject({ status: "completed" });
            expect(findUpload(erroredId)).toMatchObject({ status: "error" });
            expect(state.getBatch(batchId)?.status).toBe("cancelled");
        });

        it("is a no-op when the batch is already processing", () => {
            const uploadingId = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const processingId = state.addUploadItem(makePastedItem({ name: "b.txt" }));
            const batchId = state.addBatch(makeCollectionConfig(), [uploadingId, processingId]);

            state.updateBatchStatus(batchId, "processing");
            state.setStatus(uploadingId, "uploading");
            state.markProcessing(processingId, ["ds_2"]);

            state.cancelBatch(batchId);

            expect(state.getBatch(batchId)?.status).toBe("processing");
            expect(findUpload(uploadingId)).toMatchObject({ status: "uploading" });
            expect(findUpload(processingId)).toMatchObject({ status: "processing" });
        });
    });

    describe("cancelAll", () => {
        it("keeps standalone items in processing status unchanged while cancelling uploading ones", () => {
            const uploadingId = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const processingId = state.addUploadItem(makePastedItem({ name: "b.txt" }));

            state.setStatus(uploadingId, "uploading");
            state.markProcessing(processingId, ["ds_2"]);

            state.cancelAll();

            expect(findUpload(uploadingId)).toMatchObject({ status: "cancelled" });
            expect(findUpload(processingId)).toMatchObject({ status: "processing" });
        });

        it("leaves fully-transferred (progress 100) uploads alone so the pending response can resolve them", () => {
            const transferringId = state.addUploadItem(makePastedItem({ name: "active.txt" }));
            const transferredId = state.addUploadItem(makePastedItem({ name: "done-bytes.txt" }));

            state.setStatus(transferringId, "uploading");
            state.updateProgress(transferringId, 40);
            state.setStatus(transferredId, "uploading");
            state.updateProgress(transferredId, 100);

            state.cancelAll();

            expect(findUpload(transferringId)).toMatchObject({ status: "cancelled" });
            expect(findUpload(transferredId)).toMatchObject({ status: "uploading" });
            expect(state.hasActiveUploads.value).toBe(false);
        });

        it("keeps batches already in processing status unchanged", () => {
            const batchId = state.addBatch(makeCollectionConfig(), []);
            state.updateBatchStatus(batchId, "processing");

            state.cancelAll();

            expect(state.getBatch(batchId)?.status).toBe("processing");
        });

        it("cancels an uploading batch via cancelAll", () => {
            const id1 = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const batchId = state.addBatch(makeCollectionConfig(), [id1]);

            state.updateBatchStatus(batchId, "uploading");
            state.setStatus(id1, "uploading");

            state.cancelAll();

            expect(findUpload(id1)).toMatchObject({ status: "cancelled" });
            expect(state.getBatch(batchId)?.status).toBe("cancelled");
        });
    });

    describe("resolveBatch", () => {
        function setupProcessingBatch() {
            const firstProcessingId = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const secondProcessingId = state.addUploadItem(makePastedItem({ name: "b.txt" }));
            const cancelledId = state.addUploadItem(makePastedItem({ name: "c.txt" }));
            const batchId = state.addBatch(makeCollectionConfig(), [
                firstProcessingId,
                secondProcessingId,
                cancelledId,
            ]);

            state.setStatus(firstProcessingId, "processing");
            state.setStatus(secondProcessingId, "processing");
            state.setStatus(cancelledId, "cancelled");
            return { firstProcessingId, secondProcessingId, cancelledId, batchId };
        }

        it("markBatchResolved completes processing items and preserves cancelled ones", () => {
            const { firstProcessingId, secondProcessingId, cancelledId, batchId } = setupProcessingBatch();

            state.markBatchResolved(batchId);

            expect(findUpload(firstProcessingId)).toMatchObject({ status: "completed" });
            expect(findUpload(secondProcessingId)).toMatchObject({ status: "completed" });
            expect(findUpload(cancelledId)).toMatchObject({ status: "cancelled" });
            expect(state.getBatch(batchId)?.status).toBe("completed");
        });

        it("markBatchFailed errors processing items and preserves cancelled ones", () => {
            const { firstProcessingId, secondProcessingId, cancelledId, batchId } = setupProcessingBatch();

            state.markBatchFailed(batchId, "Collection failed to populate");

            expect(findUpload(firstProcessingId)).toMatchObject({
                status: "error",
                error: "Collection failed to populate",
            });
            expect(findUpload(secondProcessingId)).toMatchObject({ status: "error" });
            expect(findUpload(cancelledId)).toMatchObject({ status: "cancelled" });
            expect(state.getBatch(batchId)).toMatchObject({ status: "error", error: "Collection failed to populate" });
        });
    });

    describe("dismiss", () => {
        it("dismissUpload removes an errored item", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setError(id, "oops");

            state.dismissUpload(id);

            expect(findUpload(id)).toBeUndefined();
        });

        it("dismissUpload leaves non-error items alone", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "uploading");

            state.dismissUpload(id);

            expect(findUpload(id)).toBeDefined();
        });

        it("dismissBatch removes an errored batch and its items", () => {
            suppressExpectedErrorMessages(["failed"]);

            const id = state.addUploadItem(makePastedItem({ name: "a.txt" }));
            const batchId = state.addBatch(makeCollectionConfig(), [id]);
            state.setBatchError(batchId, "failed");

            state.dismissBatch(batchId);

            expect(state.getBatch(batchId)).toBeUndefined();
            expect(findUpload(id)).toBeUndefined();
        });
    });
});
