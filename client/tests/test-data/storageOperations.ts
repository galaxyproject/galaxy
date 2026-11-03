import type { StorageOperationRunSummary } from "@/utils/storageOperations";

export function getFakeStorageOperationRun(
    overrides: Partial<StorageOperationRunSummary> = {},
): StorageOperationRunSummary {
    return {
        run_id: "run-id",
        state: "pending",
        mode: "move",
        target_object_store_id: "other",
        create_time: "2026-01-01T00:00:00.000Z",
        update_time: "2026-01-01T00:00:00.000Z",
        total_count: 1,
        succeeded_count: 0,
        failed_count: 0,
        skipped_count: 0,
        total_bytes_processed: 0,
        ...overrides,
    };
}
