import { copyDataset } from "@/api/datasets";
import type { FetchDataResponse } from "@/api/tools";
import type { PreparedUpload } from "@/components/Panels/Upload/types";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { useConfig } from "@/composables/config";
import type { LibraryDatasetUploadItem, UploadedDataset } from "@/composables/upload/uploadItemTypes";
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

interface UploadResponseData {
    id: string;
    name?: string;
    label?: string;
    hid?: number;
    src?: string;
}

function isUploadResponseData(value: unknown): value is UploadResponseData {
    if (!value || typeof value !== "object") {
        return false;
    }
    // At minimum, check that it has an 'id' property which is what we actually need
    return "id" in value && typeof value.id === "string";
}

function toUploadedDataset(output: unknown): UploadedDataset | null {
    if (!isUploadResponseData(output)) {
        return null;
    }

    if (!output.id) {
        return null;
    }

    return {
        id: output.id,
        name: output.name ?? output.label ?? output.id,
        hid: output.hid,
        src: output.src === "hdca" ? "hdca" : "hda",
    };
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function collectUploadedDatasets(responseOutputs: unknown, datasets: UploadedDataset[]): void {
    if (!responseOutputs) {
        return;
    }

    if (Array.isArray(responseOutputs)) {
        responseOutputs.forEach((item) => collectUploadedDatasets(item, datasets));
        return;
    }

    const converted = toUploadedDataset(responseOutputs);
    if (converted) {
        datasets.push(converted);
        return;
    }

    if (isPlainObject(responseOutputs)) {
        Object.values(responseOutputs).forEach((nested) => collectUploadedDatasets(nested, datasets));
    }
}

function datasetsFromResponse(response: FetchDataResponse): UploadedDataset[] {
    if (!response.outputs) {
        return [];
    }

    const datasets: UploadedDataset[] = [];
    collectUploadedDatasets(response.outputs, datasets);

    // Deduplicate by dataset ID in case multiple nested paths contain the same output.
    const seen = new Set<string>();
    return datasets.filter((dataset) => {
        if (seen.has(dataset.id)) {
            return false;
        }
        seen.add(dataset.id);
        return true;
    });
}

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
                    const uploadedDatasets = datasetsFromResponse(response);

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
