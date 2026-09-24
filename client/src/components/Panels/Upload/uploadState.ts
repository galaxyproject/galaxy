import { computed } from "vue";

import type { State } from "@/components/History/Content/model/states";
import type { SupportedCollectionType } from "@/composables/upload/collectionTypes";
import type { NewUploadItem, UploadItem, UploadStatus } from "@/composables/upload/uploadItemTypes";
import { isActiveUpload, isCancellableBatchStatus, isCancellableUpload } from "@/composables/upload/uploadItemTypes";
import { useUserLocalStorage } from "@/composables/userLocalStorage";

const LOCAL_STORAGE_KEY = "uploadPanel.activeUploads";
const BATCHES_STORAGE_KEY = "uploadPanel.activeBatches";

/** Collection batch lifecycle status */
export type BatchStatus = "uploading" | "creating-collection" | "processing" | "completed" | "error" | "cancelled";

/**
 * UI-facing batch model including aggregated progress and uploads.
 * Derived from CollectionBatchState and UploadItem state.
 */
export interface BatchWithProgress extends CollectionBatchState {
    uploads: UploadItem[];
    progress: number;
    allCompleted: boolean;
    hasError: boolean;
}

/**
 * Base interface for ordered upload list items used in progress views.
 */
export interface UploadListItemBase {
    /** Discriminator for rendering */
    type: "batch" | "upload";
    /** Creation timestamp used for ordering */
    createdAt: number;
}

/** UI model for a collection batch item */
export interface UploadBatchListItem extends UploadListItemBase {
    type: "batch";
    batch: BatchWithProgress;
}

/** UI model for a standalone upload item */
export interface UploadFileListItem extends UploadListItemBase {
    type: "upload";
    upload: UploadItem;
}

/** Union of all upload list UI items */
export type UploadListItem = UploadBatchListItem | UploadFileListItem;

/**
 * Subset of the upload state API used by upload tracking utilities.
 * Provides only the functions needed for tracking and managing upload progress.
 */
export type UploadStateTrackingApi = Pick<
    ReturnType<typeof useUploadState>,
    | "addBatch"
    | "addUploadItem"
    | "getBatch"
    | "setStatus"
    | "updateProgress"
    | "setError"
    | "markProcessing"
    | "updateBatchStatus"
    | "setBatchCollectionId"
    | "setBatchError"
>;

/** Collection batch state tracking */
export interface CollectionBatchState {
    /** Unique batch identifier */
    id: string;
    /** Collection name */
    name: string;
    /** Collection type */
    type: SupportedCollectionType;
    /** Whether to hide source datasets after collection creation (two-step path only) */
    hideSourceItems: boolean;
    /** Target history ID */
    historyId: string;
    /** Upload item IDs belonging to this batch */
    uploadIds: string[];
    /** Dataset IDs created from uploads (needed for two-step collection creation) */
    datasetIds: string[];
    /** Batch processing status */
    status: BatchStatus;
    /** Created collection ID (set after successful creation) */
    collectionId?: string;
    /** Error message for batch-level failures */
    error?: string;
    /** Timestamp when batch was created */
    createdAt: number;
    /** Whether this batch uses direct HDCA creation (no separate collection creation step) */
    directCreation?: boolean;
}

function generateId() {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Statuses whose numeric progress may still change. Once an item reaches
 * processing/terminal state, progress is frozen at its final value.
 */
const PROGRESS_UPDATE_STATUSES: UploadStatus[] = ["queued", "uploading"];

// Shared state - initialized lazily on first use
let activeItems: ReturnType<typeof useUserLocalStorage<UploadItem[]>> | null = null;
let activeBatches: ReturnType<typeof useUserLocalStorage<CollectionBatchState[]>> | null = null;

function getActiveItems() {
    if (!activeItems) {
        activeItems = useUserLocalStorage<UploadItem[]>(LOCAL_STORAGE_KEY, []);
    }
    return activeItems;
}

function getActiveBatches() {
    if (!activeBatches) {
        activeBatches = useUserLocalStorage<CollectionBatchState[]>(BATCHES_STORAGE_KEY, []);
    }
    return activeBatches;
}

/**
 * Composable for managing upload state and progress tracking.
 * Persists upload items to user-specific localStorage and provides
 * reactive state for upload monitoring.
 */
export function useUploadState() {
    const items = getActiveItems();
    const batches = getActiveBatches();

    /**
     * Single mutation primitive for upload items. Applies `patch` only if the
     * item exists and its current status is in `allowedFrom` — or, when
     * `allowedFrom` is omitted, in any non-cancelled status. Cancellation is
     * terminal and can never be overridden; every status rule lives here.
     */
    function transitionItem(id: string, patch: (item: UploadItem) => void, allowedFrom?: UploadStatus[]) {
        const item = items.value.find((u) => u.id === id);
        if (!item || item.status === "cancelled" || (allowedFrom !== undefined && !allowedFrom.includes(item.status))) {
            return;
        }
        patch(item);
    }

    const hasUploads = computed(() => items.value.length > 0);

    const completedCount = computed(() => items.value.filter((i) => i.status === "completed").length);
    const errorCount = computed(() => items.value.filter((i) => i.status === "error").length);
    const cancelledCount = computed(() => items.value.filter((i) => i.status === "cancelled").length);
    const uploadingCount = computed(() => items.value.filter((i) => isActiveUpload(i.status)).length);
    const isUploading = computed(() => items.value.some((i) => isActiveUpload(i.status)));
    const hasUploadingItems = computed(() => items.value.some((i) => i.status === "uploading"));
    const hasProcessingItems = computed(() => items.value.some((i) => i.status === "processing"));

    const hasActiveUploads = computed(() => items.value.some((i) => isCancellableUpload(i)));

    const totalProgress = computed(() => {
        const nonCancelledItems = items.value.filter((i) => i.status !== "cancelled");
        if (nonCancelledItems.length === 0) {
            return 0;
        }
        const sum = nonCancelledItems.reduce((acc, file) => acc + file.progress, 0);
        return Math.round(sum / nonCancelledItems.length);
    });

    const totalSizeBytes = computed(() =>
        items.value.filter((i) => i.status !== "cancelled").reduce((sum, file) => sum + file.size, 0),
    );

    const uploadedSizeBytes = computed(() =>
        items.value
            .filter((i) => i.status !== "cancelled")
            .reduce((sum, file) => sum + (file.size * file.progress) / 100, 0),
    );

    const hasCompleted = computed(() => items.value.some((u) => u.status === "completed"));

    /**
     * Batches with aggregated upload progress and status.
     */
    const batchesWithProgress = computed(() => {
        return batches.value.map<BatchWithProgress>((batch) => {
            const batchUploads = batch.uploadIds
                .map((id) => items.value.find((item) => item.id === id))
                .filter((item): item is UploadItem => item !== undefined);

            const totalProgress =
                batchUploads.length > 0
                    ? Math.round(batchUploads.reduce((sum, u) => sum + u.progress, 0) / batchUploads.length)
                    : 0;

            const allCompleted = batchUploads.every((u) => u.status === "completed");
            const hasError = batchUploads.some((u) => u.status === "error");

            return {
                ...batch,
                uploads: batchUploads,
                progress: totalProgress,
                allCompleted,
                hasError,
            };
        });
    });

    /**
     * Upload items that are not part of any batch.
     */
    const standaloneUploads = computed(() => {
        return items.value.filter((item) => !item.batchId);
    });

    /**
     * Ordered list of upload-related items (batches and standalone uploads)
     * sorted by creation time for progress display.
     */
    const orderedUploadItems = computed<UploadListItem[]>(() => {
        const batchItems: UploadBatchListItem[] = batchesWithProgress.value.map((batch) => ({
            type: "batch",
            createdAt: batch.createdAt,
            batch,
        }));

        const standaloneItems: UploadFileListItem[] = items.value
            .filter((item) => !item.batchId)
            .map((upload) => ({
                type: "upload",
                createdAt: upload.createdAt,
                upload,
            }));

        return [...batchItems, ...standaloneItems].sort((a, b) => b.createdAt - a.createdAt);
    });

    /**
     * Adds a new upload item to the queue.
     * @param item - Upload configuration (file, URL, or pasted content)
     * @param batchId - Optional batch ID to associate this upload with
     * @returns Unique identifier for the upload
     */
    function addUploadItem(item: NewUploadItem, batchId?: string) {
        const entry = {
            ...item,
            id: generateId(),
            createdAt: Date.now(),
            progress: 0,
            status: "queued",
            error: undefined,
            batchId,
            datasetIds: [],
            datasetState: undefined,
        } satisfies UploadItem;

        items.value.push(entry);
        return entry.id;
    }

    /**
     * Creates a new collection batch.
     * @param config - Collection configuration
     * @param uploadIds - Upload IDs belonging to this batch
     * @param directCreation - Whether to use direct HDCA creation (default: false)
     * @returns Unique batch identifier
     */
    function addBatch(
        config: { name: string; type: SupportedCollectionType; hideSourceItems: boolean; historyId: string },
        uploadIds: string[],
        directCreation = false,
    ): string {
        const batch: CollectionBatchState = {
            id: generateId(),
            ...config,
            uploadIds,
            datasetIds: [],
            status: "uploading",
            error: undefined,
            collectionId: undefined,
            createdAt: Date.now(),
            directCreation,
        };

        batches.value.push(batch);
        return batch.id;
    }

    /**
     * Updates the status of a collection batch.
     * @param batchId - Batch identifier
     * @param status - New status to set
     */
    function updateBatchStatus(batchId: string, status: BatchStatus) {
        const batch = batches.value.find((b) => b.id === batchId);
        if (batch) {
            batch.status = status;
        }
    }

    /**
     * Sets the created collection ID for a batch.
     * @param batchId - Batch identifier
     * @param collectionId - Created collection ID
     */
    function setBatchCollectionId(batchId: string, collectionId: string) {
        const batch = batches.value.find((b) => b.id === batchId);
        if (batch) {
            batch.collectionId = collectionId;
        }
    }

    /**
     * Sets an error message for a batch.
     * @param batchId - Batch identifier
     * @param error - Error message
     */
    function setBatchError(batchId: string, error: string) {
        const batch = batches.value.find((b) => b.id === batchId);
        if (batch) {
            batch.error = error;
            batch.status = "error";
        }
        console.error(error);
    }

    /**
     * Gets a batch by ID.
     * @param batchId - Batch identifier
     * @returns Batch state or undefined
     */
    function getBatch(batchId: string): CollectionBatchState | undefined {
        return batches.value.find((b) => b.id === batchId);
    }

    /**
     * Adds a dataset ID to a batch's datasetIds array.
     * @param batchId - Batch identifier
     * @param datasetId - Dataset ID to add
     */
    function addBatchDatasetId(batchId: string, datasetId: string) {
        const batch = batches.value.find((b) => b.id === batchId);
        if (batch) {
            batch.datasetIds.push(datasetId);
        }
    }

    /**
     * Updates upload progress for a specific item.
     * Only updates the numeric progress value; status transitions are managed
     * by explicit actions (markProcessing, etc.).
     * @param id - Upload item identifier
     * @param progress - Progress percentage (0-100)
     */
    function updateProgress(id: string, progress: number) {
        transitionItem(
            id,
            (item) => {
                item.progress = Math.max(0, Math.min(100, Math.round(progress)));
            },
            PROGRESS_UPDATE_STATUSES,
        );
    }

    /**
     * Updates the status of an upload item.
     * Will not overwrite a cancelled item — cancellation is terminal.
     * @param id - Upload item identifier
     * @param status - New status to set
     */
    function setStatus(id: string, status: UploadStatus) {
        transitionItem(id, (item) => {
            item.status = status;
        });
    }

    /**
     * Marks an upload as failed with an error message.
     * @param id - Upload item identifier
     * @param error - Error message describing the failure
     */
    function setError(id: string, error: string) {
        transitionItem(id, (item) => {
            item.status = "error";
            item.error = error;
        });
    }

    /**
     * Marks an upload as processing (file transfer done, dataset still being processed by the backend)
     * and stores the dataset IDs for lifecycle monitoring.
     */
    function markProcessing(id: string, datasetIds: string[]) {
        transitionItem(id, (item) => {
            item.status = "processing";
            item.progress = 100;
            item.datasetIds = datasetIds;
        });
    }

    /**
     * Marks an upload as completed after its dataset(s) reach a terminal-ok state.
     */
    function markDatasetsResolved(id: string) {
        transitionItem(id, (item) => {
            item.status = "completed";
        });
    }

    /**
     * Marks an upload as failed when its dataset(s) reach an error state.
     */
    function markDatasetsFailed(id: string, message: string) {
        transitionItem(id, (item) => {
            item.status = "error";
            item.error = message;
        });
    }

    /**
     * Updates the latest known dataset state for display purposes.
     * Does not change the upload status.
     */
    function updateDatasetState(id: string, state: State) {
        transitionItem(
            id,
            (item) => {
                item.datasetState = state;
            },
            ["processing"],
        );
    }

    /**
     * Checks if an upload item can still be aborted (transfer in flight).
     */
    function isCancellable(id: string): boolean {
        const item = items.value.find((u) => u.id === id);
        return item !== undefined && isCancellableUpload(item);
    }

    /**
     * Cancels a single upload item. No-op once its transfer finished.
     * @param id - Upload item identifier
     */
    function cancelUpload(id: string) {
        const item = items.value.find((u) => u.id === id);
        if (item && isCancellableUpload(item)) {
            item.status = "cancelled";
        }
    }

    /**
     * Cancels a batch still in the transfer phase; no-op once processing or terminal.
     * @param batchId - Batch identifier
     */
    function cancelBatch(batchId: string) {
        const batch = batches.value.find((b) => b.id === batchId);
        if (!batch) {
            return;
        }
        if (!isCancellableBatchStatus(batch.status)) {
            return;
        }

        batch.status = "cancelled";
        for (const uploadId of batch.uploadIds) {
            const item = items.value.find((u) => u.id === uploadId);
            if (item && isCancellableUpload(item)) {
                item.status = "cancelled";
            }
        }
    }

    /** Cancels in-flight transfers; fully-transferred and processing items survive. */
    function cancelAll() {
        for (const item of items.value) {
            if (item.batchId) {
                continue;
            }
            if (isCancellableUpload(item)) {
                item.status = "cancelled";
            }
        }

        for (const batch of batches.value) {
            if (isCancellableBatchStatus(batch.status)) {
                cancelBatch(batch.id);
            }
        }
    }

    /**
     * Removes all completed and cancelled uploads from the list.
     */
    function clearCompleted() {
        items.value = items.value.filter((u) => u.status !== "completed" && u.status !== "cancelled");
        // Remove batches that have no remaining upload items or are completed/cancelled
        batches.value = batches.value.filter((b) => {
            if (b.status === "completed" || b.status === "cancelled") {
                return false;
            }
            // Remove batch if none of its upload items remain
            const hasRemainingItems = b.uploadIds.some((uploadId) => items.value.some((item) => item.id === uploadId));
            return hasRemainingItems;
        });
    }

    /**
     * Resolves every still-processing item of a batch, then the batch itself.
     * Shared body of markBatchResolved / markBatchFailed. Items already in a
     * terminal state are not overridden.
     * @param batchId - Batch identifier
     * @param status - Terminal status to apply to the batch and its items
     * @param message - Optional error message (when resolving to error)
     */
    function resolveBatch(batchId: string, status: "completed" | "error", message?: string) {
        const batch = batches.value.find((b) => b.id === batchId);
        if (!batch || batch.status === "cancelled") {
            return;
        }
        for (const uploadId of batch.uploadIds) {
            transitionItem(
                uploadId,
                (item) => {
                    item.status = status;
                    if (message !== undefined) {
                        item.error = message;
                    }
                },
                ["processing"],
            );
        }
        if (message !== undefined) {
            batch.error = message;
        }
        batch.status = status;
    }

    /**
     * Marks still-processing items of a batch as completed, then the batch itself.
     * Called when the HDCA reaches a terminal-ok state.
     * @param batchId - Batch identifier
     */
    function markBatchResolved(batchId: string) {
        resolveBatch(batchId, "completed");
    }

    /**
     * Marks still-processing items of a batch as errored, then the batch itself.
     * Called when the HDCA reaches an error state.
     * @param batchId - Batch identifier
     * @param message - Error message describing the failure
     */
    function markBatchFailed(batchId: string, message: string) {
        resolveBatch(batchId, "error", message);
    }

    /**
     * Removes a failed upload from the list so stuck or errored entries can be
     * dismissed individually without clearing everything.
     * @param id - Upload item identifier
     */
    function dismissUpload(id: string) {
        const index = items.value.findIndex((u) => u.id === id);
        if (index === -1 || items.value[index]?.status !== "error") {
            return;
        }
        items.value.splice(index, 1);
        for (const batch of batches.value) {
            batch.uploadIds = batch.uploadIds.filter((uploadId) => uploadId !== id);
        }
    }

    /**
     * Removes a failed batch and its upload items from the list.
     * @param batchId - Batch identifier
     */
    function dismissBatch(batchId: string) {
        const batch = batches.value.find((b) => b.id === batchId);
        if (!batch || batch.status !== "error") {
            return;
        }
        const memberIds = new Set(batch.uploadIds);
        items.value = items.value.filter((item) => !memberIds.has(item.id) && item.batchId !== batchId);
        batches.value = batches.value.filter((b) => b.id !== batchId);
    }

    /**
     * Clears all upload items from the list.
     */
    function clearAll() {
        items.value = [];
        batches.value = [];
    }

    return {
        activeItems: items,
        activeBatches: batches,
        hasUploads,
        completedCount,
        errorCount,
        cancelledCount,
        uploadingCount,
        isUploading,
        hasUploadingItems,
        hasProcessingItems,
        hasActiveUploads,
        totalProgress,
        totalSizeBytes,
        uploadedSizeBytes,
        hasCompleted,
        batchesWithProgress,
        standaloneUploads,
        orderedUploadItems,
        addUploadItem,
        addBatch,
        updateBatchStatus,
        setBatchCollectionId,
        setBatchError,
        getBatch,
        addBatchDatasetId,
        updateProgress,
        setStatus,
        setError,
        isCancellable,
        cancelUpload,
        cancelBatch,
        cancelAll,
        clearCompleted,
        clearAll,
        dismissUpload,
        dismissBatch,
        markProcessing,
        markDatasetsResolved,
        markDatasetsFailed,
        markBatchResolved,
        markBatchFailed,
        updateDatasetState,
    };
}
