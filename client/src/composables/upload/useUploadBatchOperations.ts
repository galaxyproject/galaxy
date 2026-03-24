import { createHistoryDatasetCollectionInstanceFull } from "@/api/datasetCollections";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { buildCollectionElements } from "@/composables/upload/collectionElements";
import type { NewUploadItem, UploadItem } from "@/composables/upload/uploadItemTypes";
import { validateUploadItem } from "@/composables/upload/uploadItemTypes";
import { useHistoryStore } from "@/stores/historyStore";
import { getHistoryUploadActionErrorMessage, getHistoryUploadBlockReason } from "@/utils/historyUpload";
import { errorMessageAsString } from "@/utils/simple-error";
import { toApiUploadItem, uploadCollectionDatasets } from "@/utils/upload";

interface UploadBatchOperationsOptions {
    autoRecover?: boolean;
}

let didRecoverIncompleteBatches = false;

export function useUploadBatchOperations(options: UploadBatchOperationsOptions = {}) {
    const uploadState = useUploadState();

    function findUploadItem(id: string): UploadItem | undefined {
        return uploadState.activeItems.value.find((item) => item.id === id);
    }

    async function validateTargetHistory(targetHistoryId: string): Promise<string | null> {
        const historyStore = useHistoryStore();
        let history = historyStore.getHistoryById(targetHistoryId, false) ?? null;
        if (!history) {
            await historyStore.loadHistoryById(targetHistoryId);
            history = historyStore.getHistoryById(targetHistoryId, false) ?? null;
        }
        if (!history) {
            return null;
        }
        const blockReason = getHistoryUploadBlockReason(history);
        return blockReason ? getHistoryUploadActionErrorMessage(blockReason) : null;
    }

    /**
     * Creates a dataset collection from uploaded datasets.
     *
     * @param batchId - Batch ID in upload state
     * @throws {Error} If the batch is not found, has missing data, or collection creation fails
     */
    async function createCollection(batchId: string): Promise<void> {
        const batch = uploadState.getBatch(batchId);
        if (!batch) {
            const errorMsg = `Batch not found: ${batchId}`;
            console.error(errorMsg);
            throw new Error(errorMsg);
        }

        if (batch.collectionId) {
            return;
        }

        if (!batch.datasetIds || batch.datasetIds.length === 0) {
            const errorMsg = "No dataset IDs available for collection creation";
            uploadState.setBatchError(batchId, errorMsg);
            throw new Error(errorMsg);
        }

        const items = batch.uploadIds
            .map((id) => findUploadItem(id))
            .filter((item): item is UploadItem => item !== undefined);

        if (items.length === 0) {
            const errorMsg = "No upload items available for collection creation";
            uploadState.setBatchError(batchId, errorMsg);
            throw new Error(errorMsg);
        }

        if (items.length !== batch.uploadIds.length) {
            const errorMsg = `Cannot create collection: only ${items.length} of ${batch.uploadIds.length} upload items found. This can happen after a page refresh. Please re-upload the files or manually create the collection.`;
            uploadState.setBatchError(batchId, errorMsg);
            throw new Error(errorMsg);
        }

        uploadState.updateBatchStatus(batchId, "creating-collection");

        try {
            const elementIdentifiers = buildCollectionElements(items, batch.datasetIds, batch.type);

            if (elementIdentifiers.length === 0) {
                throw new Error("No valid collection elements to create");
            }

            const response = await createHistoryDatasetCollectionInstanceFull({
                name: batch.name,
                collection_type: batch.type,
                element_identifiers: elementIdentifiers,
                history_id: batch.historyId,
                hide_source_items: batch.hideSourceItems,
                instance_type: "history",
                copy_elements: true,
                fields: "auto",
            });

            uploadState.setBatchCollectionId(batchId, response.id);
            uploadState.updateBatchStatus(batchId, "completed");
        } catch (err) {
            const errorMsg = errorMessageAsString(err);
            uploadState.setBatchError(batchId, errorMsg);

            const currentBatch = uploadState.getBatch(batchId);
            currentBatch?.uploadIds.forEach((id) => {
                const item = findUploadItem(id);
                if (item && !item.error) {
                    item.error = "Uploaded successfully, but collection creation failed";
                }
            });

            throw new Error(errorMsg);
        }
    }

    /**
     * Processes a collection batch using the direct HDCA creation path.
     * All items are uploaded together in one /api/tools/fetch request that
     * creates the collection atomically — no separate collection creation step.
     *
     * Used for non-library batches where all items can be fed to the upload API directly.
     */
    async function processDirectBatch(batchId: string, ids: string[], items: NewUploadItem[]): Promise<void> {
        const batch = uploadState.getBatch(batchId);
        if (!batch) {
            console.error(`Batch not found: ${batchId}`);
            return;
        }

        ids.forEach((id) => uploadState.setStatus(id, "uploading"));
        uploadState.updateBatchStatus(batchId, "uploading");

        try {
            const historyError = await validateTargetHistory(batch.historyId);
            if (historyError) {
                throw new Error(historyError);
            }

            for (const item of items) {
                const validationError = validateUploadItem(item);
                if (validationError) {
                    throw new Error(validationError);
                }
            }

            const apiItems = items.map((item) => toApiUploadItem(item));

            await uploadCollectionDatasets(
                apiItems,
                {
                    collectionName: batch.name,
                    collectionType: batch.type,
                },
                {
                    progress: (percentage) => {
                        ids.forEach((id) => uploadState.updateProgress(id, percentage));
                    },
                    success: () => {
                        ids.forEach((id) => uploadState.updateProgress(id, 100));
                        uploadState.updateBatchStatus(batchId, "completed");
                    },
                    error: (err) => {
                        const errorMsg = errorMessageAsString(err);
                        ids.forEach((id) => uploadState.setError(id, errorMsg));
                        uploadState.setBatchError(batchId, errorMsg);
                    },
                },
            );
        } catch (err) {
            const errorMsg = errorMessageAsString(err);
            ids.forEach((id) => uploadState.setError(id, errorMsg));
            uploadState.setBatchError(batchId, errorMsg);
        }
    }

    async function retryCollectionCreation(batchId: string): Promise<void> {
        const batch = uploadState.getBatch(batchId);
        if (!batch) {
            console.error(`Batch not found: ${batchId}`);
            return;
        }

        batch.error = undefined;
        uploadState.updateBatchStatus(batchId, "uploading");

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

    function recoverIncompleteBatches(): void {
        uploadState.activeBatches.value.forEach((batch) => {
            if (batch.collectionId || batch.status === "error" || batch.directCreation) {
                return;
            }

            const allCompleted = batch.uploadIds.every((uploadId) => {
                const upload = findUploadItem(uploadId);
                return upload?.status === "completed";
            });

            if (allCompleted && batch.uploadIds.length > 0 && batch.datasetIds.length > 0) {
                const availableItems = batch.uploadIds.filter((uploadId) => findUploadItem(uploadId) !== undefined);
                if (availableItems.length !== batch.uploadIds.length) {
                    uploadState.setBatchError(
                        batch.id,
                        "Collection creation failed: upload data lost after page refresh. Please re-upload the files to create the collection or manually create the collection.",
                    );
                    return;
                }

                createCollection(batch.id).catch((err) => {
                    console.error("Recovery failed:", err);
                    uploadState.setBatchError(batch.id, "Collection creation interrupted. Please retry manually.");
                });
            } else if (allCompleted && batch.uploadIds.length > 0) {
                uploadState.setBatchError(
                    batch.id,
                    "Collection creation interrupted and cannot be recovered. Dataset IDs not available. Please create the collection manually.",
                );
            }
        });
    }

    function clearCompleted(): void {
        uploadState.clearCompleted();
    }

    function clearAll(): void {
        uploadState.clearAll();
    }

    if (options.autoRecover !== false && !didRecoverIncompleteBatches) {
        recoverIncompleteBatches();
        didRecoverIncompleteBatches = true;
    }

    return {
        clearAll,
        clearCompleted,
        createCollection,
        processDirectBatch,
        recoverIncompleteBatches,
        retryCollectionCreation,
    };
}
