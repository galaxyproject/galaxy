import { copyDataset } from "@/api/datasets";
import type { PreparedUpload } from "@/components/Panels/Upload/types";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { useConfig } from "@/composables/config";
import type { LibraryDatasetUploadItem, UploadedDataset } from "@/composables/upload/uploadItemTypes";
import { datasetsFromFetchResponse } from "@/composables/upload/uploadResponse";
import type { TrackedUpload } from "@/composables/upload/uploadTracking";
import {
    initializeTrackedUploads,
    markTrackedCompleted,
    markTrackedError,
    splitTrackedUploadsByType,
    updateTrackedProgress,
} from "@/composables/upload/uploadTracking";
import { errorMessageAsString } from "@/utils/simple-error";
import type { UploadDatasetsConfig } from "@/utils/upload";
import { uploadCollectionDatasets, uploadDatasets } from "@/utils/upload";

/**
 * Composable that provides a centralized handler for submitting a prepared upload
 * to the Galaxy API.
 */
export function useUploadSubmission() {
    const uploadState = useUploadState();
    const { config: galaxyConfig } = useConfig();

    const initializeUploads = (prepared: PreparedUpload) => {
        const canTrackAsDirectCollectionBatch = Boolean(prepared.collectionConfig && prepared.apiItems.length > 0);
        const collectionConfig = canTrackAsDirectCollectionBatch ? prepared.collectionConfig : undefined;

        return initializeTrackedUploads(uploadState, prepared.uploadItems, {
            collectionConfig,
            directCreation: true,
            startUploading: true,
        });
    };

    /**
     * Process API-based uploads with progress tracking.
     */
    const processApiUploads = async (
        prepared: PreparedUpload,
        apiIds: string[],
        datasets: UploadedDataset[],
        trackedUploads: TrackedUpload[],
        batchId?: string,
        onProgress?: (percentage: number) => void,
    ): Promise<void> => {
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
                        const createdCollection = uploadedDatasets.find((dataset) => dataset.src === "hdca");
                        if (createdCollection) {
                            uploadState.setBatchCollectionId(batchId, createdCollection.id);
                        }
                        uploadState.updateBatchStatus(batchId, "completed");
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

            if (prepared.collectionConfig) {
                uploadCollectionDatasets(
                    prepared.apiItems,
                    {
                        collectionName: prepared.collectionConfig.name,
                        collectionType: prepared.collectionConfig.type,
                    },
                    config,
                );
            } else {
                uploadDatasets(prepared.apiItems, config);
            }
        });
    };

    /**
     * Process library dataset uploads with progress tracking.
     */
    const processLibraryUploads = async (
        libraryUploads: TrackedUpload<LibraryDatasetUploadItem>[],
        historyId: string,
        datasets: UploadedDataset[],
    ): Promise<void> => {
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
            }
            markTrackedCompleted(uploadState, [tracked.id]);
        }
    };

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
        const { trackedUploads, batchId } = initializeUploads(prepared);
        const { apiIds, libraryUploads } = splitTrackedUploadsByType(trackedUploads);

        await processApiUploads(prepared, apiIds, datasets, trackedUploads, batchId, onProgress);
        await processLibraryUploads(libraryUploads, historyId, datasets);

        return datasets;
    }

    return { submitPreparedUpload };
}
