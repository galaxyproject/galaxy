import { computed } from "vue";

import type { FetchDatasetHash } from "@/api/tools";
import { useUserLocalStorage } from "@/composables/userLocalStorage";

import type { UploadMode } from "./types";

const LOCAL_STORAGE_KEY = "uploadPanel.activeUploads";
const BATCHES_STORAGE_KEY = "uploadPanel.activeBatches";

/** Upload lifecycle status */
export type UploadStatus = "queued" | "uploading" | "processing" | "completed" | "error";

/** Collection batch lifecycle status */
export type BatchStatus = "uploading" | "creating-collection" | "completed" | "error";

/** Supported collection types */
export type SupportedCollectionType = "list" | "list:paired";

/** Collection batch state tracking */
export interface CollectionBatchState {
    /** Unique batch identifier */
    id: string;
    /** Collection name */
    name: string;
    /** Collection type */
    type: SupportedCollectionType;
    /** Whether to hide source datasets after collection creation */
    hideSourceItems: boolean;
    /** Target history ID */
    historyId: string;
    /** Upload item IDs belonging to this batch */
    uploadIds: string[];
    /** Dataset IDs created from uploads (needed for collection creation) */
    datasetIds: string[];
    /** Batch processing status */
    status: BatchStatus;
    /** Created collection ID (set after successful creation) */
    collectionId?: string;
    /** Error message for batch-level failures */
    error?: string;
    /** Timestamp when batch was created */
    createdAt: number;
}

/** Internal state tracking for an upload */
interface UploadState {
    id: string;
    status: UploadStatus;
    progress: number;
    error?: string;
    createdAt: number;
    /** Optional reference to parent batch */
    batchId?: string;
}

/** Common properties shared by all upload item types */
interface UploadItemCommon {
    uploadMode: UploadMode;
    name: string;
    size: number;
    targetHistoryId: string;
    dbkey: string;
    extension: string;
    spaceToTab: boolean;
    toPosixLines: boolean;
    deferred: boolean;
    hashes?: FetchDatasetHash[];
}

/** Upload item from a local file */
export interface LocalFileUploadItem extends UploadItemCommon {
    uploadMode: "local-file";
    /** File handle (not persisted in localStorage) */
    fileData?: File;
}

/** Upload item from pasted text content */
export interface PastedContentUploadItem extends UploadItemCommon {
    uploadMode: "paste-content";
    content: string;
}

/** Upload item from a URL */
export interface UrlUploadItem extends UploadItemCommon {
    uploadMode: "paste-links";
    url: string;
}

export type NewUploadItem = LocalFileUploadItem | PastedContentUploadItem | UrlUploadItem;

/** Upload item with state tracking */
export type UploadItem = NewUploadItem & UploadState;

function generateId() {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

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

    const hasUploads = computed(() => items.value.length > 0);

    const completedCount = computed(() => items.value.filter((i) => i.status === "completed").length);
    const errorCount = computed(() => items.value.filter((i) => i.status === "error").length);
    const uploadingCount = computed(
        () => items.value.filter((i) => i.status === "uploading" || i.status === "processing").length,
    );
    const isUploading = computed(() => items.value.some((i) => i.status === "uploading" || i.status === "processing"));

    const totalProgress = computed(() => {
        if (items.value.length === 0) {
            return 0;
        }
        const sum = items.value.reduce((acc, file) => acc + file.progress, 0);
        return Math.round(sum / items.value.length);
    });

    const totalSizeBytes = computed(() => items.value.reduce((sum, file) => sum + file.size, 0));

    const uploadedSizeBytes = computed(() =>
        items.value.reduce((sum, file) => sum + (file.size * file.progress) / 100, 0),
    );

    const hasCompleted = computed(() => items.value.some((u) => u.status === "completed"));

    /**
     * Batches with aggregated upload progress and status.
     */
    const batchesWithProgress = computed(() => {
        return batches.value.map((batch) => {
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
        } satisfies UploadItem;

        items.value.push(entry);
        return entry.id;
    }

    /**
     * Creates a new collection batch.
     * @param config - Collection configuration
     * @param uploadIds - Upload IDs belonging to this batch
     * @returns Unique batch identifier
     */
    function addBatch(
        config: { name: string; type: SupportedCollectionType; hideSourceItems: boolean; historyId: string },
        uploadIds: string[],
    ): string {
        const batch: CollectionBatchState = {
            id: generateId(),
            ...config,
            uploadIds,
            datasetIds: [],
            status: "uploading",
            createdAt: Date.now(),
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
     * Automatically marks as completed when progress reaches 100%.
     * @param id - Upload item identifier
     * @param progress - Progress percentage (0-100)
     */
    function updateProgress(id: string, progress: number) {
        const item = items.value.find((u) => u.id === id);
        if (item) {
            item.progress = Math.max(0, Math.min(100, Math.round(progress)));
            if (item.progress >= 100 && item.status !== "error") {
                item.status = "completed";
            }
        }
    }

    /**
     * Updates the status of an upload item.
     * @param id - Upload item identifier
     * @param status - New status to set
     */
    function setStatus(id: string, status: UploadStatus) {
        const item = items.value.find((u) => u.id === id);
        if (item) {
            item.status = status;
        }
    }

    /**
     * Marks an upload as failed with an error message.
     * @param id - Upload item identifier
     * @param error - Error message describing the failure
     */
    function setError(id: string, error: string) {
        const item = items.value.find((u) => u.id === id);
        if (item) {
            item.status = "error";
            item.error = error;
        }
    }

    /**
     * Removes all completed uploads from the list.
     */
    function clearCompleted() {
        items.value = items.value.filter((u) => u.status !== "completed");
        // Remove batches where all uploads are completed
        batches.value = batches.value.filter((b) => b.status !== "completed");
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
        uploadingCount,
        isUploading,
        totalProgress,
        totalSizeBytes,
        uploadedSizeBytes,
        hasCompleted,
        batchesWithProgress,
        standaloneUploads,
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
        clearCompleted,
        clearAll,
    };
}
