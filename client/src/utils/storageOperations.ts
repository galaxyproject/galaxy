import type { components } from "@/api/schema";

export type StorageOperationRunState = components["schemas"]["StorageOperationRunState"];
export type StorageOperationRunSummary = components["schemas"]["StorageOperationRunSummary"];
export type DatasetStorageOperationFailureReasonCode =
    components["schemas"]["DatasetStorageOperationFailureReasonCode"];
export type TrackedStorageRun = StorageOperationRunSummary & {
    historyId: string;
    runUrl: string;
};

export interface IneligibleReasonDescription {
    label: string;
    description: string;
}

/**
 * Mapping of storage operation reason codes to user-friendly labels and descriptions.
 * These correspond to the DatasetStorageOperationFailureReasonCode enum defined in the backend API schema.
 */
const REASON_CODE_DESCRIPTIONS: Record<DatasetStorageOperationFailureReasonCode, IneligibleReasonDescription> = {
    dataset_not_found: {
        label: "Dataset not found",
        description: "The dataset could not be found at the time of the operation.",
    },
    invalid_target_object_store: {
        label: "Invalid storage location",
        description: "The selected storage location is not available or is invalid.",
    },
    missing_source_object_store: {
        label: "Missing source location",
        description: "The dataset does not have a source storage location defined.",
    },
    already_in_target: {
        label: "Already in target location",
        description: "The dataset is already stored in the selected location.",
    },
    target_quota_exceeded: {
        label: "Target quota exceeded",
        description: "The operation would exceed the target storage quota.",
    },
    shared_dataset: {
        label: "Shared dataset",
        description: "This dataset is referenced by histories you do not own and cannot be moved.",
    },
    insufficient_permissions: {
        label: "Insufficient permissions",
        description: "You do not have permission to move this dataset to a different storage location.",
    },
    dataset_in_use: {
        label: "Dataset in use",
        description: "The dataset is currently being used by an active job and cannot be moved.",
    },
    target_expiration_imminent: {
        label: "Would expire soon in target location",
        description:
            "Moving this dataset would leave less than 10 days before expiration in the selected target location.",
    },
    checksum_verification_failed: {
        label: "Checksum verification failed",
        description:
            "The data transfer could not be verified: the source and target checksums do not match. The original data is unchanged.",
    },
    execution_error: {
        label: "Execution error",
        description: "An error occurred while attempting to move the dataset.",
    },
};

/**
 * Get a user-friendly description for a storage operation reason code.
 * @param reasonCode - The reason code from the backend
 * @returns An object with a human-readable label and description
 */
export function getIneligibleReasonDescription(reasonCode: string): IneligibleReasonDescription {
    return (
        REASON_CODE_DESCRIPTIONS[reasonCode as DatasetStorageOperationFailureReasonCode] || {
            label: "Unknown reason",
            description: `Reason code: ${reasonCode}`,
        }
    );
}

/**
 * Check if a storage operation run state is a terminal state (no longer running).
 * @param state - The run state (e.g., "pending", "running", "completed", "failed")
 * @returns true if the state is terminal (completed or failed)
 */
export function isTerminalRunState(state?: StorageOperationRunState): boolean {
    return state === "completed" || state === "failed";
}

export function toTrackedStorageRun(historyId: string, run: StorageOperationRunSummary): TrackedStorageRun {
    const createTime = run.create_time || new Date().toISOString();
    const updateTime = run.update_time || createTime;

    return {
        ...run,
        create_time: createTime,
        update_time: updateTime,
        historyId,
        runUrl: `/histories/${historyId}/storage/runs/${run.run_id}`,
    };
}

export function getCompletedAtForRun(run: StorageOperationRunSummary): string | undefined {
    return isTerminalRunState(run.state) ? run.update_time : undefined;
}
