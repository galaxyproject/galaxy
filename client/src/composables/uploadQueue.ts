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
import type { FetchDataResponse } from "@/api/tools";
import type { NewUploadItem, SupportedCollectionType } from "@/components/Panels/Upload/uploadState";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { errorMessageAsString } from "@/utils/simple-error";
import type { UploadItem } from "@/utils/upload";
import { createFileUploadItem, createPastedUploadItem, createUrlUploadItem, uploadDatasets } from "@/utils/upload";

/** Collection creation input from UI components */
export interface CollectionCreationInput {
    /** Name of the collection to create */
    name: string;
    /** Type of collection: 'list' or 'list:paired' */
    type: SupportedCollectionType;
}

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
 * Extracts common prefix from pair of file names for smart pair naming.
 * Removes common suffixes like _R1/_R2, _1/_2, _F/_R, etc.
 *
 * @param name1 - First file name
 * @param name2 - Second file name
 * @returns Common prefix or empty string if no clear pattern
 */
function extractPairName(name1: string, name2: string): string {
    // Remove file extensions
    const base1 = name1.replace(/\.[^.]+$/, "");
    const base2 = name2.replace(/\.[^.]+$/, "");

    // Common paired-end patterns to detect and remove
    const patterns = [
        { regex: /[._-]?R?[12]$/, replace: "" }, // _R1, _R2, _1, _2, .R1, .R2
        { regex: /[._-]?[FR]$/, replace: "" }, // _F, _R, .F, .R
        { regex: /[._-]?read[12]$/i, replace: "" }, // _read1, _read2
        { regex: /[._-]?fwd$|[._-]?rev$/i, replace: "" }, // _fwd, _rev
        { regex: /[._-]?forward$|[._-]?reverse$/i, replace: "" }, // _forward, _reverse
    ];

    // Try each pattern
    for (const pattern of patterns) {
        const test1 = base1.replace(pattern.regex, pattern.replace);
        const test2 = base2.replace(pattern.regex, pattern.replace);

        if (test1 === test2 && test1.length > 0) {
            return test1;
        }
    }

    // Fallback: find longest common prefix
    let i = 0;
    while (i < Math.min(base1.length, base2.length) && base1[i] === base2[i]) {
        i++;
    }

    if (i > 0) {
        // Trim trailing separators
        return base1.slice(0, i).replace(/[._-]+$/, "");
    }

    // Last resort: use first file's base name
    return base1;
}

/**
 * Builds collection element identifiers based on collection type.
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

            const basePairName = extractPairName(item1.name, item2.name) || `pair_${Math.floor(i / 2) + 1}`;
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
 * Converts a UI upload item to an API-ready UploadItem.
 *
 * This bridges the gap between:
 * - NewUploadItem: UI-friendly format with camelCase (persisted in localStorage)
 * - UploadItem: API-ready format with snake_case (sent to server)
 *
 * @param item - The UI upload item to convert
 * @returns API-ready upload item
 * @throws Error if item has invalid uploadMode or missing required data
 */
export function toUploadItem(item: NewUploadItem): UploadItem {
    const baseOptions = {
        name: item.name,
        size: item.size,
        dbkey: item.dbkey,
        ext: item.extension,
        space_to_tab: item.spaceToTab,
        to_posix_lines: item.toPosixLines,
        deferred: item.deferred,
        hashes: item.hashes,
    };

    switch (item.uploadMode) {
        case "local-file":
            if (!item.fileData) {
                throw new Error(`No file data for upload item: ${item.name}`);
            }
            return createFileUploadItem(item.fileData, item.targetHistoryId, baseOptions);

        case "paste-content":
            return createPastedUploadItem(item.content, item.targetHistoryId, baseOptions);

        case "paste-links":
            return createUrlUploadItem(item.url, item.targetHistoryId, baseOptions);

        default:
            throw new Error(`Unknown upload mode: ${(item as NewUploadItem).uploadMode}`);
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
            if (!item.url || item.url.trim().length === 0) {
                return `No URL provided for "${item.name}"`;
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
        const batch = batches.find((b) => b.ids[0] && batchState.uploadIds.includes(b.ids[0]));
        const items =
            batch?.items ||
            batchState.uploadIds
                .map((id) => uploadState.activeItems.value.find((u) => u.id === id))
                .filter((item): item is NonNullable<typeof item> => item !== undefined);

        if (items.length === 0) {
            const errorMsg = "No upload items available for collection creation";
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
            batchState.uploadIds.forEach((id) => {
                const item = uploadState.activeItems.value.find((i) => i.id === id);
                if (item && !item.error) {
                    item.error = `Uploaded successfully, but collection creation failed: ${errorMsg}`;
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
            const item = uploadState.activeItems.value.find((i) => i.id === id);
            if (item && item.error?.includes("collection creation failed")) {
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
     * Processes the next upload in the queue.
     * Handles upload submission with progress tracking and error handling.
     */
    async function processNext(): Promise<void> {
        if (processing || queue.length === 0) {
            return;
        }

        const id = queue.shift()!;
        const item = uploadState.activeItems.value.find((i) => i.id === id);

        if (!item) {
            // Item was removed from state (e.g., user cleared it), skip to next
            return processNext();
        }

        processing = true;
        uploadState.setStatus(id, "uploading");

        try {
            // Pre-validate before attempting upload
            const validationError = validateUploadItem(item);
            if (validationError) {
                throw new Error(validationError);
            }

            // Convert to API format and upload
            const uploadItem = toUploadItem(item);

            // Find the batch this upload belongs to
            const batch = batches.find((b) => b.ids.includes(id));
            const batchId = item.batchId;

            await uploadDatasets([uploadItem], {
                progress: (percentage) => uploadState.updateProgress(id, percentage),
                success: (response: FetchDataResponse) => {
                    uploadState.updateProgress(id, 100);

                    // Collect dataset IDs for collection creation
                    if (batch && batchId && response.outputs) {
                        // The outputs field is Record<string, unknown> but is actually an array of dataset objects
                        const outputs = response.outputs as unknown as Array<{
                            id: string;
                            hid?: number;
                            name?: string;
                        }>;
                        const datasetId = outputs[0]?.id;
                        if (datasetId) {
                            // Store in both internal batch and persisted state
                            batch.datasetIds.push(datasetId);
                            uploadState.addBatchDatasetId(batchId, datasetId);
                        }

                        // Check if all batch uploads are complete
                        const allComplete = batch.ids.every((uploadId) => {
                            const batchItem = uploadState.activeItems.value.find((i) => i.id === uploadId);
                            return batchItem?.status === "completed" || batchItem?.status === "error";
                        });

                        // If batch is complete, create collection
                        if (allComplete) {
                            createCollection(batchId).catch((err) => {
                                console.error("Unexpected collection creation error:", err);
                            });
                        }
                    }
                },
                error: (err) => {
                    // This callback is for upload-specific errors
                    uploadState.setError(id, errorMessageAsString(err));
                },
            });
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
        let batchId: string | undefined;

        // If collection config provided, create a batch in state
        if (collectionConfig) {
            // Create batch first to get the ID
            batchId = uploadState.addBatch(collectionConfig, []);
        }

        // Add upload items with batch ID
        const ids = items.map((item) => uploadState.addUploadItem(item, batchId));

        // Update batch with upload IDs
        if (batchId && collectionConfig) {
            const batch = uploadState.getBatch(batchId);
            if (batch) {
                batch.uploadIds = ids;
            }

            // Create internal batch for dataset ID tracking
            batches.push({
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
            const batch = batches[i];
            if (!batch) {
                continue;
            }

            const hasActiveUploads = batch.ids.some((id) =>
                uploadState.activeItems.value.some((item) => item.id === id),
            );

            if (!hasActiveUploads) {
                batches.splice(i, 1);
            }
        }
    }

    /**
     * Recovers incomplete collection creation on initialization.
     * Checks for batches where uploads completed but collection wasn't created.
     */
    function recoverIncompleteBatches(): void {
        uploadState.activeBatches.value.forEach((batch) => {
            // Skip if collection already created or batch has errors
            if (batch.collectionId || batch.status === "error") {
                return;
            }

            // Check if all uploads in batch are completed
            const allCompleted = batch.uploadIds.every((uploadId) => {
                const upload = uploadState.activeItems.value.find((u) => u.id === uploadId);
                return upload?.status === "completed";
            });

            // If uploads are complete and we have dataset IDs, try to create the collection
            if (allCompleted && batch.uploadIds.length > 0 && batch.datasetIds.length > 0) {
                console.log(`Recovering incomplete batch: ${batch.name}`);
                // Attempt to create the collection
                createCollection(batch.id).catch((err) => {
                    console.error("Recovery failed:", err);
                    uploadState.setBatchError(batch.id, "Collection creation interrupted. Please retry manually.");
                });
            } else if (allCompleted && batch.uploadIds.length > 0) {
                // Uploads complete but no dataset IDs (shouldn't happen, but handle gracefully)
                uploadState.setBatchError(
                    batch.id,
                    "Collection creation interrupted and cannot be recovered. Dataset IDs not available.",
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
