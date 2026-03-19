import { createHistoryDatasetCollectionInstanceFull } from "@/api/datasetCollections";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { buildCollectionElements } from "@/composables/upload/collectionElements";
import type { UploadItem } from "@/composables/upload/uploadItemTypes";
import { errorMessageAsString } from "@/utils/simple-error";

interface UploadBatchOperationsOptions {
    autoRecover?: boolean;
}

let didRecoverIncompleteBatches = false;

export function useUploadBatchOperations(options: UploadBatchOperationsOptions = {}) {
    const uploadState = useUploadState();

    function findUploadItem(id: string): UploadItem | undefined {
        return uploadState.activeItems.value.find((item) => item.id === id);
    }

    /**
     * Creates a dataset collection from uploaded datasets.
     *
     * @param batchId - Batch ID in upload state
     */
    async function createCollection(batchId: string): Promise<void> {
        const batch = uploadState.getBatch(batchId);
        if (!batch) {
            console.error(`Batch not found: ${batchId}`);
            return;
        }

        if (batch.collectionId) {
            return;
        }

        if (!batch.datasetIds || batch.datasetIds.length === 0) {
            uploadState.setBatchError(batchId, "No dataset IDs available for collection creation");
            return;
        }

        const items = batch.uploadIds
            .map((id) => findUploadItem(id))
            .filter((item): item is UploadItem => item !== undefined);

        if (items.length === 0) {
            uploadState.setBatchError(batchId, "No upload items available for collection creation");
            return;
        }

        if (items.length !== batch.uploadIds.length) {
            uploadState.setBatchError(
                batchId,
                `Cannot create collection: only ${items.length} of ${batch.uploadIds.length} upload items found. This can happen after a page refresh. Please re-upload the files or manually create the collection.`,
            );
            return;
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
        recoverIncompleteBatches,
        retryCollectionCreation,
    };
}
