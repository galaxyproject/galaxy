import { suppressExpectedErrorMessages } from "@tests/vitest/helpers";
import flushPromises from "flush-promises";
import { http, HttpResponse } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { makeCollectionConfig, makePastedItem, makeUrlItem } from "@/composables/upload/testHelpers/uploadFixtures";

import { useUploadBatchOperations } from "./useUploadBatchOperations";

const { server } = useServerMock();

describe("useUploadBatchOperations", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        useUploadState().clearAll();
    });

    afterEach(() => {
        vi.restoreAllMocks();
        useUploadState().clearAll();
    });

    it("processes the direct collection path atomically", async () => {
        server.use(
            http.get("/api/configuration", () => HttpResponse.json({ chunk_upload_size: 42 })),
            http.post("/api/tools/fetch", async ({ request }) => {
                const body = await request.json();
                expect(body).toMatchObject({
                    history_id: "hist_1",
                    targets: [
                        {
                            destination: { type: "hdca" },
                            collection_type: "list",
                            name: "My Collection",
                        },
                    ],
                });
                return HttpResponse.json({ outputs: [{ id: "hdca_1", src: "hdca" }] });
            }),
        );

        const state = useUploadState();
        const operations = useUploadBatchOperations({ autoRecover: false });
        const first = makeUrlItem({ name: "a.txt" });
        const second = makeUrlItem({ name: "b.txt" });
        const batchId = state.addBatch(makeCollectionConfig(), [], true);
        const id1 = state.addUploadItem(first, batchId);
        const id2 = state.addUploadItem(second, batchId);
        state.getBatch(batchId)!.uploadIds = [id1, id2];

        await operations.processDirectBatch(batchId, [id1, id2], [first, second]);

        expect(state.getBatch(batchId)?.status).toBe("completed");
        expect(state.activeItems.value.every((item) => item.status === "completed")).toBe(true);
    });

    it("retries collection creation after an earlier two-step failure", async () => {
        suppressExpectedErrorMessages(["Temporary error"]);
        server.use(http.post("/api/dataset_collections", () => HttpResponse.json({ id: "col_retried" })));

        const state = useUploadState();
        const operations = useUploadBatchOperations({ autoRecover: false });
        const uploadId = state.addUploadItem(makePastedItem());
        state.updateProgress(uploadId, 100);

        const batchId = state.addBatch(makeCollectionConfig(), [uploadId], false);
        state.addBatchDatasetId(batchId, "ds_1");
        state.setBatchError(batchId, "Temporary error");

        const item = state.activeItems.value.find((entry) => entry.id === uploadId);
        if (item) {
            item.error = "Uploaded successfully, but collection creation failed";
        }

        await operations.retryCollectionCreation(batchId);

        expect(state.getBatch(batchId)?.status).toBe("completed");
        expect(state.getBatch(batchId)?.collectionId).toBe("col_retried");
        expect(state.activeItems.value.find((entry) => entry.id === uploadId)?.error).toBeUndefined();
    });

    it("recovers interrupted two-step collection creation from persisted state", async () => {
        server.use(http.post("/api/dataset_collections", () => HttpResponse.json({ id: "col_recovered" })));

        const state = useUploadState();
        const itemId = state.addUploadItem(makePastedItem({ name: "recovered.txt" }));
        state.setStatus(itemId, "uploading");
        state.updateProgress(itemId, 100);

        const batchId = state.addBatch(
            { name: "Recovery Collection", type: "list", hideSourceItems: false, historyId: "hist_1" },
            [itemId],
            false,
        );
        state.addBatchDatasetId(batchId, "ds_recovered");

        const operations = useUploadBatchOperations({ autoRecover: false });
        operations.recoverIncompleteBatches();
        await flushPromises();

        expect(state.getBatch(batchId)?.collectionId).toBe("col_recovered");
        expect(state.getBatch(batchId)?.status).toBe("completed");
    });
});
