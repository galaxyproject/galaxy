import { suppressExpectedErrorMessages } from "@tests/vitest/helpers";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { makeCollectionConfig, makePastedItem, makeUrlItem } from "@/composables/upload/testHelpers/uploadFixtures";
import { setupTestPinia } from "@/stores/testUtils";

import { useUploadBatchOperations } from "./useUploadBatchOperations";

const { server, http } = useServerMock();

describe("useUploadBatchOperations", () => {
    beforeEach(() => {
        setupTestPinia();
        useUploadState().clearAll();
    });

    afterEach(() => {
        vi.restoreAllMocks();
        useUploadState().clearAll();
    });

    it("processes the direct collection path atomically", async () => {
        server.use(
            http.get("/api/configuration", ({ response }) =>
                response.untyped(HttpResponse.json({ chunk_upload_size: 42 })),
            ),
            http.post("/api/tools/fetch", async ({ request, response }) => {
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
                return response.untyped(HttpResponse.json({ outputs: [], output_collections: [{ id: "hdca_1" }] }));
            }),
        );

        const state = useUploadState();
        const operations = useUploadBatchOperations({ autoRecover: false });
        const first = makeUrlItem({ name: "a.txt" });
        const second = makeUrlItem({ name: "b.txt" });
        const batchId = state.addBatch(makeCollectionConfig(), [], true);
        const uploadIds = [state.addUploadItem(first, batchId), state.addUploadItem(second, batchId)];
        state.getBatch(batchId)!.uploadIds = uploadIds;

        await operations.processDirectBatch(batchId, uploadIds, [first, second]);

        expect(state.getBatch(batchId)?.status).toBe("processing");
        expect(state.getBatch(batchId)?.collectionId).toBe("hdca_1");
        expect(state.activeItems.value.map((item) => item.status)).toEqual(["processing", "processing"]);
    });

    it("retries collection creation after an earlier two-step failure", async () => {
        suppressExpectedErrorMessages(["Temporary error"]);
        server.use(
            http.post("/api/dataset_collections", ({ response }) =>
                response.untyped(HttpResponse.json({ id: "col_retried" })),
            ),
        );

        const state = useUploadState();
        const operations = useUploadBatchOperations({ autoRecover: false });
        const uploadId = state.addUploadItem(makePastedItem());
        state.setStatus(uploadId, "completed");

        const batchId = state.addBatch(makeCollectionConfig(), [uploadId], false);
        state.addBatchDatasetId(batchId, "ds_1");
        state.setBatchError(batchId, "Temporary error");

        const item = state.activeItems.value.find((entry) => entry.id === uploadId)!;
        item.error = "Uploaded successfully, but collection creation failed";

        await operations.retryCollectionCreation(batchId);

        expect(state.getBatch(batchId)?.status).toBe("processing");
        expect(state.getBatch(batchId)?.collectionId).toBe("col_retried");
        const retriedItem = state.activeItems.value.find((entry) => entry.id === uploadId);
        expect(retriedItem).toBeDefined();
        expect(retriedItem?.error).toBeUndefined();
    });

    it("recovers interrupted two-step collection creation from persisted state", async () => {
        server.use(
            http.post("/api/dataset_collections", ({ response }) =>
                response.untyped(HttpResponse.json({ id: "col_recovered" })),
            ),
        );

        const state = useUploadState();
        const itemId = state.addUploadItem(makePastedItem({ name: "recovered.txt" }));
        state.setStatus(itemId, "completed");

        const batchId = state.addBatch(makeCollectionConfig({ name: "Recovery Collection" }), [itemId], false);
        state.addBatchDatasetId(batchId, "ds_recovered");

        const operations = useUploadBatchOperations({ autoRecover: false });
        operations.recoverIncompleteBatches();
        await flushPromises();

        expect(state.getBatch(batchId)?.collectionId).toBe("col_recovered");
        expect(state.getBatch(batchId)?.status).toBe("processing");
    });
});
