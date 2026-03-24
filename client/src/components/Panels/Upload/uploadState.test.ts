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
            state.updateProgress(completedId, 100); // auto-marks as completed
            state.setError(erroredId, "network error");

            expect(state.uploadingCount.value).toBe(1);
            expect(state.completedCount.value).toBe(1);
            expect(state.errorCount.value).toBe(1);
            expect(state.isUploading.value).toBe(true);
            expect(state.hasCompleted.value).toBe(true);
        });

        it("isUploading is false when no items are in uploading or processing state", () => {
            const id = state.addUploadItem(makePastedItem());
            state.updateProgress(id, 100); // completed

            expect(state.isUploading.value).toBe(false);
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

        it("reaching 100% auto-transitions item status to completed", () => {
            const id = state.addUploadItem(makePastedItem());
            state.setStatus(id, "uploading");
            state.updateProgress(id, 100);

            const item = state.activeItems.value.find((i) => i.id === id)!;
            expect(item.status).toBe("completed");
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
            state.updateProgress(id1, 100);
            state.updateProgress(id2, 100);

            const bwp = state.batchesWithProgress.value.find((b) => b.id === batchId)!;
            expect(bwp.allCompleted).toBe(true);
            expect(bwp.progress).toBe(100);
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
            state.updateProgress(completedId, 100);
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
            state.updateProgress(id1, 100);
            state.updateProgress(id2, 100);

            state.clearCompleted();

            expect(state.activeBatches.value.find((b) => b.id === batchId)).toBeUndefined();
        });

        it("keeps a batch with at least one non-completed item after clearing", () => {
            const completedId = state.addUploadItem(makePastedItem("done.txt"));
            const uploadingId = state.addUploadItem(makePastedItem("active.txt"));
            const batchId = state.addBatch(BATCH_CONFIG, [completedId, uploadingId]);
            state.updateProgress(completedId, 100);
            state.setStatus(uploadingId, "uploading");

            state.clearCompleted();

            // Batch stays because uploadingId is still active
            expect(state.activeBatches.value.find((b) => b.id === batchId)).toBeDefined();
            // But the completed item is gone
            expect(state.activeItems.value.find((i) => i.id === completedId)).toBeUndefined();
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
});
