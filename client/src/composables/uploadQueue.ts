/**
 * Upload queue composable for managing dataset uploads to Galaxy.
 *
 * This composable provides a queue-based upload system that:
 * - Converts UI upload items to API-ready format
 * - Processes uploads sequentially with progress tracking
 * - Persists upload state for UI monitoring
 * - Creates dataset collections after successful batch uploads
 */
import { copyDataset } from "@/api/datasets";
import type { FetchDataResponse } from "@/api/tools";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import type { UploadCollectionConfig } from "@/composables/upload/collectionTypes";
import type { CompositeFileUploadItem, NewUploadItem } from "@/composables/upload/uploadItemTypes";
import { datasetIdsFromFetchResponse } from "@/composables/upload/uploadResponse";
import { initializeTrackedUploads } from "@/composables/upload/uploadTracking";
import { useUploadBatchOperations } from "@/composables/upload/useUploadBatchOperations";
import { useHistoryStore } from "@/stores/historyStore";
import { getHistoryUploadActionErrorMessage, getHistoryUploadBlockReason } from "@/utils/historyUpload";
import { errorMessageAsString } from "@/utils/simple-error";
import {
    createFileUploadItem,
    createPastedUploadItem,
    createUrlUploadItem,
    toApiUploadItem,
    uploadCollectionDatasets,
    uploadDatasets,
} from "@/utils/upload";

/**
 * Represents a batch of uploads that will be combined into a dataset collection
 * after all uploads complete successfully.
 */
interface CollectionBatch {
    /** Batch ID used in the persisted upload state */
    batchId: string;
    /** Upload item IDs belonging to this batch */
    ids: string[];
    /** Original upload items (needed for building collection elements) */
    items: NewUploadItem[];
    /** Dataset IDs collected from successful upload responses */
    datasetIds: string[];
    /** Collection configuration specifying name, type, target history, and options */
    collectionConfig: UploadCollectionConfig;
}

/**
 * Validates a UI upload item before conversion.
 * Returns an error message if invalid, undefined if valid.
 *
 * @param item - The upload item to validate
 * @returns Error message if invalid, undefined if valid
 */
export function validateUploadItem(item: NewUploadItem): string | undefined {
    switch (item.uploadMode) {
        case "local-file":
            if (!item.fileData) {
                return `No file selected for "${item.name}"`;
            }
            if (item.fileData.size === 0) {
                return `File "${item.name}" is empty`;
            }
            break;

        case "paste-content":
            if (!item.content || item.content.trim().length === 0) {
                return `No content provided for "${item.name}"`;
            }
            break;

        case "paste-links":
        case "remote-files":
            if (!item.url || item.url.trim().length === 0) {
                return `No URL provided for "${item.name}"`;
            }
            break;

        case "data-library":
            if (!item.lddaId) {
                return `No library dataset ID provided for "${item.name}"`;
            }
            break;

        case "composite-file": {
            if (!item.extension || item.extension === "auto") {
                return `No composite type selected for "${item.name}"`;
            }
            for (const slot of item.slots) {
                if (slot.optional) {
                    continue;
                }
                const isEmpty =
                    (slot.src === "files" && !slot.file) ||
                    (slot.src === "url" && !slot.url?.trim()) ||
                    (slot.src === "paste" && !slot.content?.trim());
                if (isEmpty) {
                    return `Required slot "${slot.slotName}" has no content for "${item.name}"`;
                }
            }
            break;
        }

        default:
            return `Unknown upload mode: ${(item as NewUploadItem).uploadMode}`;
    }
    return undefined;
}

/**
 * Composable for managing upload queue and processing.
 *
 * Provides methods to enqueue different types of uploads and track their progress.
 * Uses the shared upload state for persistence and UI updates.
 * Supports automatic collection creation after batch uploads.
 *
 * @example
 * ```typescript
 * const uploadQueue = useUploadQueue();
 *
 * // Enqueue files for upload
 * const ids = uploadQueue.enqueue([
 *   { uploadMode: "local-file", fileData: file, ... },
 *   { uploadMode: "paste-links", url: "http://...", ... },
 * ]);
 *
 * // Clear completed uploads
 * uploadQueue.clearCompleted();
 * ```
 */
export function useUploadQueue() {
    const uploadState = useUploadState();
    const uploadBatchOperations = useUploadBatchOperations({ autoRecover: false });
    const historyStore = useHistoryStore();
    const queue: string[] = [];
    const batches: CollectionBatch[] = [];
    let processing = false;

    /**
     * Helper to find an upload item by ID from the active items.
     */
    function findUploadItem(id: string) {
        return uploadState.activeItems.value.find((i) => i.id === id);
    }

    /**
     * Stores a dataset ID in both the internal batch and persisted state.
     *
     * @param batch - Internal batch tracking object
     * @param datasetId - Dataset ID to store
     */
    function collectDatasetId(batch: CollectionBatch | undefined, datasetId: string) {
        if (batch) {
            batch.datasetIds.push(datasetId);
            uploadState.addBatchDatasetId(batch.batchId, datasetId);
        }
    }

    /**
     * Checks if all uploads in a batch have completed (success or error).
     *
     * @param batch - Internal batch tracking object
     * @returns True if all uploads are complete
     */
    function isBatchComplete(batch: CollectionBatch): boolean {
        return batch.ids.every((uploadId) => {
            const item = findUploadItem(uploadId);
            return item?.status === "completed" || item?.status === "error";
        });
    }

    /**
     * Checks batch completion status and triggers collection creation if ready.
     *
     * @param batch - Internal batch tracking object
     */
    async function checkAndCompleteBatch(batch?: CollectionBatch): Promise<void> {
        if (!batch) {
            return;
        }

        if (isBatchComplete(batch)) {
            await uploadBatchOperations.createCollection(batch.batchId).catch((err) => {
                uploadState.setBatchError(batch.batchId, errorMessageAsString(err));
            });
        }
    }

    /**
     * Determines if a collection batch should use direct HDCA creation.
     * Returns false for batches containing data-library items (which need the two-step approach
     * since they use copyDataset instead of /api/tools/fetch).
     */
    function canUseDirectCollection(batch: CollectionBatch): boolean {
        return batch.items.every((item) => item.uploadMode !== "data-library");
    }

    async function validateTargetHistory(targetHistoryId: string): Promise<string | null> {
        let history = historyStore.getHistoryById(targetHistoryId, false) ?? null;
        if (!history) {
            await historyStore.loadHistoryById(targetHistoryId);
            history = historyStore.getHistoryById(targetHistoryId, false) ?? null;
        }

        // If history still cannot be resolved, treat as no validation error here
        // (downstream upload logic will surface appropriate API errors if needed)
        if (!history) {
            return null;
        }

        const blockReason = getHistoryUploadBlockReason(history);
        return blockReason ? getHistoryUploadActionErrorMessage(blockReason) : null;
    }

    /**
     * Processes an entire collection batch as a single HDCA upload.
     * All items are uploaded together in one /api/tools/fetch request with
     * destination { type: "hdca" }, creating the collection atomically.
     */
    async function processCollectionBatch(batch: CollectionBatch): Promise<void> {
        const { batchId, items, collectionConfig } = batch;

        // Mark all items as uploading
        batch.ids.forEach((id) => uploadState.setStatus(id, "uploading"));
        uploadState.updateBatchStatus(batchId, "uploading");

        try {
            const historyError = await validateTargetHistory(collectionConfig.historyId);
            if (historyError) {
                throw new Error(historyError);
            }

            // Validate all items first
            for (const item of items) {
                const validationError = validateUploadItem(item);
                if (validationError) {
                    throw new Error(validationError);
                }
            }

            // Convert all UI items to API items
            const apiItems = items.map((item) => toApiUploadItem(item));

            await uploadCollectionDatasets(
                apiItems,
                {
                    collectionName: collectionConfig.name,
                    collectionType: collectionConfig.type,
                },
                {
                    progress: (percentage) => {
                        batch.ids.forEach((id) => uploadState.updateProgress(id, percentage));
                    },
                    success: (_response: FetchDataResponse) => {
                        batch.ids.forEach((id) => uploadState.updateProgress(id, 100));
                        uploadState.updateBatchStatus(batchId, "completed");
                    },
                    error: (err) => {
                        const errorMsg = errorMessageAsString(err);
                        batch.ids.forEach((id) => uploadState.setError(id, errorMsg));
                        uploadState.setBatchError(batchId, errorMsg);
                    },
                },
            );
        } catch (err) {
            const errorMsg = errorMessageAsString(err);
            batch.ids.forEach((id) => uploadState.setError(id, errorMsg));
            uploadState.setBatchError(batchId, errorMsg);
        }
    }

    /**
     * Processes a library dataset upload by importing it to the target history.
     *
     * @param id - Upload item ID
     * @param item - Upload item with library dataset details
     * @param batch - Internal batch tracking object (if part of a batch)
     */
    async function processLibraryDatasetUpload(
        id: string,
        item: NewUploadItem,
        batch?: CollectionBatch,
    ): Promise<void> {
        if (item.uploadMode !== "data-library") {
            throw new Error("Invalid upload mode for library dataset upload");
        }

        uploadState.updateProgress(id, 50);

        // Import library dataset to history
        const response = await copyDataset(item.lddaId, item.targetHistoryId, "dataset", "library");

        uploadState.updateProgress(id, 100);

        // Collect dataset ID for collection creation
        // Response is an HDA (HistoryDatasetAssociation) which has an id field
        if (response && "id" in response && response.id) {
            collectDatasetId(batch, response.id);
        }

        // Check if batch is ready for collection creation
        await checkAndCompleteBatch(batch);
    }

    /**
     * Processes a composite upload by converting each slot into an ApiUploadItem
     * and submitting them together as a single composite dataset.
     *
     * @param id - Upload item ID
     * @param item - CompositeFileUploadItem with all slot data
     */
    async function processCompositeFileUpload(id: string, item: CompositeFileUploadItem): Promise<void> {
        const baseOptions = {
            dbkey: item.dbkey,
            ext: item.extension,
            space_to_tab: item.spaceToTab,
            to_posix_lines: item.toPosixLines,
            deferred: false,
        };
        // Build one ApiUploadItem per slot, all sharing the dataset-level ext/dbkey/name
        const slotApiItems = item.slots
            .filter((slot) => slot.src !== "files" || !!slot.file) // skip empty optional local-file slots
            .map((slot) => {
                const slotOptions = {
                    name: slot.slotName,
                    ...baseOptions,
                };

                if (slot.src === "files") {
                    return createFileUploadItem(slot.file!, item.targetHistoryId, {
                        ...slotOptions,
                        size: slot.file!.size,
                    });
                } else if (slot.src === "url") {
                    return createUrlUploadItem(slot.url!, item.targetHistoryId, {
                        ...slotOptions,
                        size: 0,
                    });
                } else {
                    return createPastedUploadItem(slot.content ?? "", item.targetHistoryId, {
                        ...slotOptions,
                        size: (slot.content ?? "").length,
                    });
                }
            });

        await uploadDatasets(slotApiItems, {
            composite: true,
            compositeName: item.name,
            progress: (percentage) => uploadState.updateProgress(id, percentage),
            success: () => {
                uploadState.updateProgress(id, 100);
            },
            error: (err) => {
                uploadState.setError(id, errorMessageAsString(err));
            },
        });
    }

    /**
     * Processes a regular upload (file, URL, or pasted content) via the upload API.
     *
     * @param id - Upload item ID
     * @param item - Upload item to process
     * @param batch - Internal batch tracking object (if part of a batch)
     */
    async function processRegularUpload(id: string, item: NewUploadItem, batch?: CollectionBatch): Promise<void> {
        const uploadItem = toApiUploadItem(item);

        await uploadDatasets([uploadItem], {
            progress: (percentage) => uploadState.updateProgress(id, percentage),
            success: (response: FetchDataResponse) => {
                uploadState.updateProgress(id, 100);

                // Collect dataset IDs for collection creation
                if (batch && response.outputs) {
                    const datasetId = datasetIdsFromFetchResponse(response)[0];
                    if (datasetId) {
                        collectDatasetId(batch, datasetId);
                    }

                    // Check if batch is ready for collection creation
                    checkAndCompleteBatch(batch);
                }
            },
            error: (err) => {
                uploadState.setError(id, errorMessageAsString(err));
            },
        });
    }

    /**
     * Processes the next upload in the queue.
     * Orchestrates upload execution by delegating to specialized handlers.
     *
     * When the next item belongs to a collection batch that can use direct
     * HDCA creation, all items in the batch are processed together in a
     * single /api/tools/fetch request instead of one-by-one.
     */
    async function processNext(): Promise<void> {
        if (processing || queue.length === 0) {
            return;
        }

        const id = queue[0]!; // Peek, don't remove yet
        const item = findUploadItem(id);

        if (!item) {
            queue.shift();
            // Item was removed from state (e.g., user cleared it), skip to next
            return processNext();
        }

        // Check if this item belongs to a collection batch that can use direct creation
        const batch = batches.find((b) => b.ids.includes(id));
        if (batch && canUseDirectCollection(batch)) {
            // Remove all batch items from queue at once
            for (const batchItemId of batch.ids) {
                const idx = queue.indexOf(batchItemId);
                if (idx !== -1) {
                    queue.splice(idx, 1);
                }
            }

            processing = true;
            try {
                await processCollectionBatch(batch);
            } finally {
                processing = false;
                processNext();
            }
            return;
        }

        // Single-item processing (non-collection or data-library fallback)
        queue.shift();
        processing = true;
        uploadState.setStatus(id, "uploading");

        try {
            const historyError = await validateTargetHistory(item.targetHistoryId);
            if (historyError) {
                throw new Error(historyError);
            }

            // Pre-validate before attempting upload
            const validationError = validateUploadItem(item);
            if (validationError) {
                throw new Error(validationError);
            }

            // Delegate to appropriate upload handler based on upload mode
            if (item.uploadMode === "data-library") {
                await processLibraryDatasetUpload(id, item, batch);
            } else if (item.uploadMode === "composite-file") {
                await processCompositeFileUpload(id, item);
            } else {
                await processRegularUpload(id, item, batch);
            }
        } catch (err) {
            // This catches validation errors and any unexpected errors
            uploadState.setError(id, errorMessageAsString(err));
        } finally {
            processing = false;
            processNext();
        }
    }

    /**
     * Enqueues items and starts processing.
     *
     * @param items - Array of upload items to enqueue
     * @param collectionConfig - Optional collection configuration for creating a collection from uploaded datasets
     * @returns Array of upload IDs for tracking
     */
    function enqueue(items: NewUploadItem[], collectionConfig?: UploadCollectionConfig): string[] {
        // Determine if this batch can use direct HDCA creation
        const isDirectCreation =
            collectionConfig !== undefined && items.every((item) => item.uploadMode !== "data-library");

        const { trackedUploads, batchId } = initializeTrackedUploads(uploadState, items, {
            collectionConfig,
            directCreation: isDirectCreation,
            startUploading: false,
        });
        const ids = trackedUploads.map((tracked) => tracked.id);

        // Create internal batch for queue-specific tracking
        if (batchId && collectionConfig) {
            batches.push({
                batchId,
                ids,
                items,
                datasetIds: [],
                collectionConfig,
            });
        }

        queue.push(...ids);
        processNext();
        return ids;
    }

    /**
     * Removes batches that no longer have any active upload items.
     * Called when uploads are cleared from the state.
     */
    function cleanupOrphanedBatches(): void {
        for (let i = batches.length - 1; i >= 0; i--) {
            const batch = batches[i]!;
            const hasActiveUploads = batch.ids.some((id) => findUploadItem(id) !== undefined);

            if (!hasActiveUploads) {
                batches.splice(i, 1);
            }
        }
    }

    // Initialize: recover any incomplete batches from previous session
    uploadBatchOperations.recoverIncompleteBatches();

    /** Removes all completed uploads from the state */
    function clearCompleted(): void {
        uploadState.clearCompleted();
        cleanupOrphanedBatches();
    }

    /** Clears all uploads from the state */
    function clearAll(): void {
        uploadState.clearAll();
        batches.length = 0; // Clear all batches when clearing all uploads
    }

    return {
        enqueue,
        clearCompleted,
        clearAll,
        retryCollectionCreation: uploadBatchOperations.retryCollectionCreation,
        /** Access to upload state for UI components */
        state: uploadState,
    };
}
