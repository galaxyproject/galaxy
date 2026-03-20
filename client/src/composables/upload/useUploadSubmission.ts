import { copyDataset } from "@/api/datasets";
import type { PreparedUpload } from "@/components/Panels/Upload/types";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { useConfig } from "@/composables/config";
import type { LibraryDatasetUploadItem, UploadedDataset } from "@/composables/upload/uploadItemTypes";
import { datasetsFromFetchResponse } from "@/composables/upload/uploadResponse";
import type { InitializedUploads, TrackedUpload } from "@/composables/upload/uploadTracking";
import {
    initializeTrackedUploads,
    markTrackedCompleted,
    markTrackedError,
    splitTrackedUploadsByType,
    updateTrackedProgress,
} from "@/composables/upload/uploadTracking";
import { useUploadBatchOperations } from "@/composables/upload/useUploadBatchOperations";
import { errorMessageAsString } from "@/utils/simple-error";
import type { UploadDatasetsConfig } from "@/utils/upload";
import { isFetchApiCompatible, uploadCollectionDatasets, uploadDatasets } from "@/utils/upload";

/**
 * Composable that provides a centralized handler for submitting a prepared upload
 * to the Galaxy API.
 */
export function useUploadSubmission() {
    const uploadState = useUploadState();
    const uploadBatchOperations = useUploadBatchOperations({ autoRecover: false });
    const { config: galaxyConfig } = useConfig();

    function initializeUploads(prepared: PreparedUpload): InitializedUploads {
        const collectionConfig = prepared.collectionConfig;
        const directCreation = isDirectCollectionCreation(prepared);

        return initializeTrackedUploads(uploadState, prepared.uploadItems, {
            collectionConfig,
            directCreation,
            startUploading: true,
        });
    }

    /**
     * Determines if the prepared upload is for direct collection creation.
     * Data library items are not compatible with direct collection creation because
     * they require copying datasets rather than uploading files, so the presence of any
     * data library items means we cannot do direct collection creation.
     */
    function isDirectCollectionCreation(prepared: PreparedUpload): boolean {
        return Boolean(prepared.collectionConfig && prepared.uploadItems?.every(isFetchApiCompatible));
    }

    /**
     * Process API-based uploads with progress tracking.
     *
     * This function handles the upload of file-based items through the Galaxy API,
     * supporting both regular dataset uploads and direct collection creation. Progress
     * is tracked via callbacks and the upload state store.
     */
    async function processApiUploads(
        prepared: PreparedUpload,
        apiIds: string[],
        datasets: UploadedDataset[],
        trackedUploads: TrackedUpload[],
        batchId?: string,
        directCollectionCreation?: boolean,
        onProgress?: (percentage: number) => void,
    ): Promise<void> {
        if (prepared.apiItems.length === 0) {
            return;
        }

        return new Promise<void>((resolve, reject) => {
            const config: UploadDatasetsConfig = {
                chunkSize: galaxyConfig.value.chunk_upload_size as number,
                success: (response) => {
                    const uploadedDatasets = datasetsFromFetchResponse(response);

                    markTrackedCompleted(uploadState, apiIds);
                    datasets.push(...uploadedDatasets);

                    if (batchId) {
                        if (directCollectionCreation) {
                            const createdCollection = uploadedDatasets.find((dataset) => dataset.src === "hdca");
                            if (createdCollection) {
                                uploadState.setBatchCollectionId(batchId, createdCollection.id);
                            }
                            uploadState.updateBatchStatus(batchId, "completed");
                        } else {
                            uploadedDatasets
                                .filter((dataset) => dataset.src === "hda")
                                .forEach((dataset) => uploadState.addBatchDatasetId(batchId, dataset.id));
                        }
                    }

                    resolve();
                },
                error: (uploadError) => {
                    const errorMessage = errorMessageAsString(uploadError);

                    markTrackedError(uploadState, trackedUploads, errorMessage);
                    if (batchId) {
                        uploadState.setBatchError(batchId, errorMessage);
                    }
                    reject(uploadError);
                },
                progress: (percentage) => {
                    onProgress?.(percentage);
                    updateTrackedProgress(uploadState, apiIds, percentage);
                },
            };

            if (prepared.collectionConfig && directCollectionCreation) {
                uploadCollectionDatasets(
                    prepared.apiItems,
                    {
                        collectionName: prepared.collectionConfig.name,
                        collectionType: prepared.collectionConfig.type,
                    },
                    config,
                );
            } else {
                uploadDatasets(prepared.apiItems, {
                    ...config,
                    composite: prepared.uploadOptions?.composite,
                    compositeName: prepared.uploadOptions?.compositeName,
                });
            }
        });
    }

    /**
     * Process library dataset uploads with progress tracking.
     *
     * This function copies datasets from data libraries into the current history.
     * Each library dataset is processed sequentially, with progress tracking for each item.
     *
     * @param libraryUploads - Array of tracked library upload items to process
     * @param historyId - The target history ID to copy datasets into
     * @param datasets - Array to collect successfully copied datasets
     * @param batchId - Optional batch ID for batch upload tracking
     * @returns Promise that resolves when all library uploads complete
     */
    async function processLibraryUploads(
        libraryUploads: TrackedUpload<LibraryDatasetUploadItem>[],
        historyId: string,
        datasets: UploadedDataset[],
        batchId?: string,
    ): Promise<void> {
        for (const tracked of libraryUploads) {
            uploadState.updateProgress(tracked.id, 50);
            const copied = await copyDataset(tracked.item.lddaId, historyId, "dataset", "library");
            if (copied && "id" in copied && copied.id) {
                const copiedName =
                    "name" in copied && typeof copied.name === "string" ? copied.name : tracked.item.name;
                const copiedHid = "hid" in copied && typeof copied.hid === "number" ? copied.hid : undefined;

                datasets.push({
                    id: copied.id,
                    name: copiedName,
                    hid: copiedHid,
                    src: "hda",
                });
                if (batchId) {
                    uploadState.addBatchDatasetId(batchId, copied.id);
                }
            }
            markTrackedCompleted(uploadState, [tracked.id]);
        }
    }

    /**
     * Submit a prepared upload to Galaxy and return the resulting datasets.
     *
     * Progress is tracked automatically in the upload state store so the
     * progress panel reflects upload status. An optional `onProgress` callback
     * can be used by the caller to update its own local progress indicator
     * (e.g. the modal progress bar).
     */
    async function submitPreparedUpload(
        historyId: string,
        prepared: PreparedUpload,
        onProgress?: (percentage: number) => void,
    ): Promise<UploadedDataset[]> {
        const datasets: UploadedDataset[] = [];
        const directCollectionCreation = isDirectCollectionCreation(prepared);
        const { trackedUploads, batchId } = initializeUploads(prepared);
        const { apiIds, libraryUploads } = splitTrackedUploadsByType(trackedUploads);

        await processApiUploads(
            prepared,
            apiIds,
            datasets,
            trackedUploads,
            batchId,
            directCollectionCreation,
            onProgress,
        );
        await processLibraryUploads(libraryUploads, historyId, datasets, batchId);

        if (batchId && prepared.collectionConfig && !directCollectionCreation) {
            await uploadBatchOperations.createCollection(batchId);
        }

        return datasets;
    }

    return { submitPreparedUpload };
}
