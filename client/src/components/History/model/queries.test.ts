import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type {
    HistoryReference,
    StorageOperationExecuteResponse,
    StorageOperationPreviewResponse,
    StorageOperationRunResponse,
} from "@/api/histories";
import { useStorageRunWatcher } from "@/composables/useStorageRunWatcher";

import { bulkStorageExecute, bulkStoragePreview, bulkStorageRunStatus } from "./queries";

const HISTORY: HistoryReference = { id: "history1", model_class: "History" };
const SNAPSHOT_ID = "aaaabbbb-0000-1111-2222-333344445555";
const RUN_ID = "ccccdddd-0000-1111-2222-333344445555";

const PREVIEW_RESPONSE: StorageOperationPreviewResponse = {
    snapshot_id: SNAPSHOT_ID,
    expires_at: "2099-01-01T00:00:00",
    selection_counts: { selected_items_count: 1, expanded_leaf_count: 1, unique_dataset_count: 1 },
    eligibility: {
        eligible_count: 1,
        ineligible_count: 0,
        reasons: [],
    },
    estimates: { bytes_to_transfer: 0, quota_delta_transfers: [] },
    warnings: [],
};

const EXECUTE_RESPONSE: StorageOperationExecuteResponse = {
    run: {
        run_id: RUN_ID,
        state: "pending",
        mode: "move",
        target_object_store_id: "other",
        create_time: "2099-01-01T00:00:00",
        update_time: "2099-01-01T00:00:00",
        total_count: 1,
        succeeded_count: 0,
        failed_count: 0,
        skipped_count: 0,
        total_bytes_processed: 0,
    },
};

const RUN_PENDING_RESPONSE: StorageOperationRunResponse = {
    run: { ...EXECUTE_RESPONSE.run },
    items: [],
};

const RUN_COMPLETED_RESPONSE: StorageOperationRunResponse = {
    run: {
        ...EXECUTE_RESPONSE.run,
        state: "completed",
        succeeded_count: 1,
        total_bytes_processed: 42,
    },
    items: [
        {
            dataset_id: "ds1",
            state: "succeeded",
            reason_code: null,
            bytes_processed: 0,
            create_time: "2099-01-01T00:00:00",
            update_time: "2099-01-01T00:00:00",
        },
    ],
};

const RUN_FAILED_RESPONSE: StorageOperationRunResponse = {
    run: {
        ...EXECUTE_RESPONSE.run,
        state: "completed",
        failed_count: 1,
        total_bytes_processed: 0,
    },
    items: [
        {
            dataset_id: "ds1",
            state: "failed",
            reason_code: "already_in_target",
            bytes_processed: 0,
            create_time: "2099-01-01T00:00:00",
            update_time: "2099-01-01T00:00:00",
        },
    ],
};

const { server, http } = useServerMock();

describe("bulkStoragePreview", () => {
    it("posts to the preview endpoint and returns snapshot data", async () => {
        server.use(
            http.post("/api/histories/{history_id}/contents/bulk/storage/preview", ({ response }) =>
                response(200).json(PREVIEW_RESPONSE),
            ),
        );

        const result = await bulkStoragePreview(HISTORY, "other", {}, []);

        expect(result).toBeDefined();
        expect(result!.snapshot_id).toBe(SNAPSHOT_ID);
        expect(result!.eligibility.eligible_count).toBe(1);
        expect(result!.eligibility.ineligible_count).toBe(0);
    });

    it("propagates server errors as exceptions", async () => {
        server.use(
            http.post("/api/histories/{history_id}/contents/bulk/storage/preview", ({ response }) =>
                response("4XX").json({ err_msg: "Not found", err_code: 404 }, { status: 404 }),
            ),
        );

        await expect(bulkStoragePreview(HISTORY, "other", {}, [])).rejects.toThrow();
    });
});

describe("bulkStorageExecute", () => {
    it("posts snapshot_id and execution_policy and returns run summary", async () => {
        server.use(
            http.post("/api/histories/{history_id}/contents/bulk/storage/execute", ({ response }) =>
                response(200).json(EXECUTE_RESPONSE),
            ),
        );

        const result = await bulkStorageExecute(HISTORY, SNAPSHOT_ID);

        expect(result!.run.run_id).toBe(RUN_ID);
        expect(result!.run.state).toBe("pending");
    });

    it("propagates server errors as exceptions", async () => {
        server.use(
            http.post("/api/histories/{history_id}/contents/bulk/storage/execute", ({ response }) =>
                response("4XX").json({ err_msg: "Snapshot expired", err_code: 400 }, { status: 400 }),
            ),
        );

        await expect(bulkStorageExecute(HISTORY, SNAPSHOT_ID)).rejects.toThrow();
    });
});

describe("bulkStorageRunStatus", () => {
    it("fetches run status summary", async () => {
        server.use(
            http.get("/api/histories/{history_id}/contents/bulk/storage/runs/{run_id}", ({ response }) =>
                response(200).json(RUN_FAILED_RESPONSE),
            ),
        );

        const result = await bulkStorageRunStatus(HISTORY, RUN_ID);

        expect(result!.run.failed_count).toBe(1);
    });
});

describe("useStorageRunWatcher", () => {
    it("starts as non-terminal and reflects the latest polled state", async () => {
        server.use(
            http.get("/api/histories/{history_id}/contents/bulk/storage/runs/{run_id}", ({ response }) =>
                response(200).json(RUN_PENDING_RESPONSE),
            ),
        );

        const { runStatus, isTerminal, startPolling } = useStorageRunWatcher(HISTORY, RUN_ID);

        expect(isTerminal.value).toBe(false);
        expect(runStatus.value).toBeNull();

        startPolling();
        await flushPromises();

        expect(runStatus.value!.run.state).toBe("pending");
        expect(isTerminal.value).toBe(false);
    });

    it("marks isTerminal=true when run reaches completed state and stops polling", async () => {
        server.use(
            http.get("/api/histories/{history_id}/contents/bulk/storage/runs/{run_id}", ({ response }) =>
                response(200).json(RUN_COMPLETED_RESPONSE),
            ),
        );

        const { runStatus, isTerminal, startPolling } = useStorageRunWatcher(HISTORY, RUN_ID);

        startPolling();
        await flushPromises();

        expect(runStatus.value!.run.state).toBe("completed");
        expect(isTerminal.value).toBe(true);
    });

    it("marks isTerminal=true when run reaches failed state", async () => {
        server.use(
            http.get("/api/histories/{history_id}/contents/bulk/storage/runs/{run_id}", ({ response }) =>
                response(200).json(RUN_FAILED_RESPONSE),
            ),
        );

        const { isTerminal, startPolling } = useStorageRunWatcher(HISTORY, RUN_ID);

        startPolling();
        await flushPromises();

        expect(isTerminal.value).toBe(true);
    });

    it("tracks run state for failure runs", async () => {
        server.use(
            http.get("/api/histories/{history_id}/contents/bulk/storage/runs/{run_id}", ({ response }) =>
                response(200).json(RUN_FAILED_RESPONSE),
            ),
        );

        const { runStatus, startPolling } = useStorageRunWatcher(HISTORY, RUN_ID);

        startPolling();
        await flushPromises();

        expect(runStatus.value!.run.state).toBe("completed");
        expect(runStatus.value!.run.failed_count).toBe(1);
    });
});
