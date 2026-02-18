/**
 * Upload queue composable for managing dataset uploads to Galaxy.
 *
 * This composable provides a queue-based upload system that:
 * - Converts UI upload items to API-ready format
 * - Processes uploads sequentially with progress tracking
 * - Persists upload state for UI monitoring
 * - Creates dataset collections after successful batch uploads
 */
import type { CollectionElementIdentifiers } from "@/api";
import { createHistoryDatasetCollectionInstanceFull } from "@/api/datasetCollections";
import { copyDataset } from "@/api/datasets";
import type { FetchDataResponse } from "@/api/tools";
import {
    COMMON_FILTERS,
    DEFAULT_FILTER,
    guessInitialFilterType,
    guessNameForPair,
} from "@/components/Collections/pairing";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import type { CollectionCreationInput, SupportedCollectionType } from "@/composables/upload/collectionTypes";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";
import { errorMessageAsString } from "@/utils/simple-error";
import { toApiUploadItem, uploadCollectionDatasets, uploadDatasets } from "@/utils/upload";

/**
 * Collection configuration for batch uploads that will be combined
 * into a collection after uploads complete.
 */
export interface CollectionConfig extends CollectionCreationInput {
    /** Whether to hide source datasets after collection creation */
    hideSourceItems: boolean;
    /** Target history ID where the collection will be created */
    historyId: string;
}

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
    collectionConfig: CollectionConfig;
}

/**
 * Builds collection element identifiers based on collection type.
 * Uses the shared pairing abstractions from @/components/Collections/pairing for
 * pair name extraction (synchronized with the backend via auto_pairing_spec.yml).
 *
 * @param items - Upload items with dataset IDs
 * @param datasetIds - Array of created dataset IDs (in upload order)
 * @param collectionType - Type of collection to create
 * @returns Collection element identifiers ready for API
 */
function buildCollectionElements(
    items: NewUploadItem[],
    datasetIds: string[],
    collectionType: SupportedCollectionType,
): CollectionElementIdentifiers {
    if (collectionType === "list") {
        // Simple list: one element per dataset
        return items.map((item, index) => ({
            name: item.name || `element_${index + 1}`,
            src: "hda" as const,
            id: datasetIds[index],
        }));
    } else {
        // List of pairs: group consecutive files into pairs
        const pairs: CollectionElementIdentifiers = [];
        const usedNames = new Set<string>();

        // Use the shared filter detection to determine forward/reverse naming convention
        const filterType = guessInitialFilterType(items) ?? DEFAULT_FILTER;
        const [forwardFilter, reverseFilter] = COMMON_FILTERS[filterType];

        for (let i = 0; i < items.length; i += 2) {
            if (i + 1 >= items.length) {
                // Odd number of files - skip last one or handle as error
                console.warn(`Skipping unpaired file at index ${i}: ${items[i]?.name}`);
                break;
            }

            const item1 = items[i];
            const item2 = items[i + 1];

            if (!item1 || !item2) {
                continue;
            }

            const basePairName =
                guessNameForPair(item1, item2, forwardFilter, reverseFilter, true) || `pair_${Math.floor(i / 2) + 1}`;
            let pairName = basePairName;

            // Ensure unique pair names by adding suffix if needed
            let counter = 1;
            while (usedNames.has(pairName)) {
                pairName = `${basePairName}_${counter}`;
                counter++;
            }
            usedNames.add(pairName);

            pairs.push({
                collection_type: "paired",
                src: "new_collection" as const,
                name: pairName,
                element_identifiers: [
                    {
                        name: "forward",
                        src: "hda" as const,
                        id: datasetIds[i],
                    },
                    {
                        name: "reverse",
                        src: "hda" as const,
                        id: datasetIds[i + 1],
                    },
                ],
            });
        }

        return pairs;
    }
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
     * Creates a dataset collection from uploaded datasets.
     *
     * @param batchId - Batch ID in upload state
     */
    async function createCollection(batchId: string): Promise<void> {
        const batchState = uploadState.getBatch(batchId);
        if (!batchState) {
            console.error(`Batch not found: ${batchId}`);
            return;
        }

        // Check if collection already created (avoid duplicates on retry)
        if (batchState.collectionId) {
            console.log(`Collection already created for batch ${batchId}: ${batchState.collectionId}`);
            return;
        }

        const { name, type, hideSourceItems, historyId, datasetIds } = batchState;

        // Check if we have dataset IDs (either from persisted state or internal batch)
        if (!datasetIds || datasetIds.length === 0) {
            const errorMsg = "No dataset IDs available for collection creation";
            uploadState.setBatchError(batchId, errorMsg);
            return;
        }

        // Get upload items to build collection elements
        // Try internal batch first (has full item data), fall back to state
        const batch = batches.find((b) => b.batchId === batchId);
        const items =
            batch?.items ||
            batchState.uploadIds
                .map((id) => findUploadItem(id))
                .filter((item): item is NonNullable<typeof item> => item !== undefined);

        if (items.length === 0) {
            const errorMsg = "No upload items available for collection creation";
            uploadState.setBatchError(batchId, errorMsg);
            return;
        }

        // Validate items have required data
        if (items.length !== batchState.uploadIds.length) {
            const errorMsg = `Cannot create collection: only ${items.length} of ${batchState.uploadIds.length} upload items found. This can happen after a page refresh. Please re-upload the files or manually create the collection.`;
            uploadState.setBatchError(batchId, errorMsg);
            return;
        }

        uploadState.updateBatchStatus(batchId, "creating-collection");

        try {
            // Build element identifiers based on collection type
            const elementIdentifiers = buildCollectionElements(items, datasetIds, type);

            if (elementIdentifiers.length === 0) {
                throw new Error("No valid collection elements to create");
            }

            // Create collection using the API
            const response = await createHistoryDatasetCollectionInstanceFull({
                name,
                collection_type: type,
                element_identifiers: elementIdentifiers,
                history_id: historyId,
                hide_source_items: hideSourceItems,
                instance_type: "history",
                copy_elements: true,
                fields: "auto",
            });

            uploadState.setBatchCollectionId(batchId, response.id);
            uploadState.updateBatchStatus(batchId, "completed");

            console.log(`Successfully created ${type} collection: ${name} (${response.id})`);
        } catch (err) {
            // Collection creation failed - datasets are still uploaded
            const errorMsg = errorMessageAsString(err);
            console.error("Collection creation failed:", errorMsg);

            uploadState.setBatchError(batchId, errorMsg);

            // Mark all batch items with error message (non-fatal)
            const batchForError = uploadState.getBatch(batchId);
            batchForError?.uploadIds.forEach((id) => {
                const item = findUploadItem(id);
                if (item && !item.error) {
                    item.error = `Uploaded successfully, but collection creation failed`;
                }
            });
        }
    }

    /**
     * Retries collection creation for a failed batch.
     * @param batchId - Batch ID to retry
     */
    async function retryCollectionCreation(batchId: string): Promise<void> {
        const batch = uploadState.getBatch(batchId);
        if (!batch) {
            console.error(`Batch not found: ${batchId}`);
            return;
        }

        // Reset error state
        batch.error = undefined;
        uploadState.updateBatchStatus(batchId, "uploading");

        // Clear error messages from individual upload items
        batch.uploadIds.forEach((id) => {
            const item = findUploadItem(id);
            if (item?.error?.includes("collection creation failed")) {
                item.error = undefined;
            }
        });

        try {
            await createCollection(batchId);
        } catch (err) {
            uploadState.setBatchError(batchId, `Retry failed: ${errorMessageAsString(err)}`);
        }
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
            await createCollection(batch.batchId).catch((err) => {
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
                    // The outputs field is Record<string, unknown> but is actually an array of dataset objects
                    const outputs = response.outputs as unknown as Array<{
                        id: string;
                        hid?: number;
                        name?: string;
                    }>;
                    const datasetId = outputs[0]?.id;
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
            // Pre-validate before attempting upload
            const validationError = validateUploadItem(item);
            if (validationError) {
                throw new Error(validationError);
            }

            // Delegate to appropriate upload handler based on upload mode
            if (item.uploadMode === "data-library") {
                await processLibraryDatasetUpload(id, item, batch);
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
    function enqueue(items: NewUploadItem[], collectionConfig?: CollectionConfig): string[] {
        // Determine if this batch can use direct HDCA creation
        const isDirectCreation =
            collectionConfig !== undefined && items.every((item) => item.uploadMode !== "data-library");

        // Create batch first if collection config provided
        const batchId = collectionConfig ? uploadState.addBatch(collectionConfig, [], isDirectCreation) : undefined;

        // Add upload items with batch ID
        const ids = items.map((item) => uploadState.addUploadItem(item, batchId));

        // Update batch with upload IDs and create internal batch for tracking
        if (batchId) {
            const batch = uploadState.getBatch(batchId);
            if (batch) {
                batch.uploadIds = ids;
            }

            batches.push({
                batchId,
                ids,
                items,
                datasetIds: [],
                collectionConfig: collectionConfig!,
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

    /**
     * Recovers incomplete collection creation on initialization.
     * Checks for batches where uploads completed but collection wasn't created.
     *
     * For direct-creation batches, there's no separate collection creation step
     * to recover — if the upload was interrupted, the user must re-upload.
     */
    function recoverIncompleteBatches(): void {
        uploadState.activeBatches.value.forEach((batch) => {
            // Skip if collection already created or batch has errors
            if (batch.collectionId || batch.status === "error") {
                return;
            }

            // Direct-creation batches don't have a separate collection creation step
            if (batch.directCreation) {
                return;
            }

            // Two-step batch recovery (data-library fallback path)
            // Check if all uploads in batch are completed
            const allCompleted = batch.uploadIds.every((uploadId) => {
                const upload = findUploadItem(uploadId);
                return upload?.status === "completed";
            });

            // If uploads are complete and we have dataset IDs, try to create the collection
            if (allCompleted && batch.uploadIds.length > 0 && batch.datasetIds.length > 0) {
                console.log(`Recovering incomplete batch: ${batch.name}`);

                // Check if we still have the upload items (they might be lost after refresh)
                const availableItems = batch.uploadIds.filter((uploadId) => findUploadItem(uploadId) !== undefined);

                if (availableItems.length !== batch.uploadIds.length) {
                    uploadState.setBatchError(
                        batch.id,
                        `Collection creation failed: upload data lost after page refresh. Please re-upload the files to create the collection or manually create the collection.`,
                    );
                    return;
                }

                // Attempt to create the collection
                createCollection(batch.id).catch((err) => {
                    console.error("Recovery failed:", err);
                    uploadState.setBatchError(batch.id, "Collection creation interrupted. Please retry manually.");
                });
            } else if (allCompleted && batch.uploadIds.length > 0) {
                // Uploads complete but no dataset IDs (shouldn't happen, but handle gracefully)
                uploadState.setBatchError(
                    batch.id,
                    "Collection creation interrupted and cannot be recovered. Dataset IDs not available. Please create the collection manually.",
                );
            }
        });
    }

    // Initialize: recover any incomplete batches from previous session
    recoverIncompleteBatches();

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
        retryCollectionCreation,
        /** Access to upload state for UI components */
        state: uploadState,
    };
}
