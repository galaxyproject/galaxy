import { copyDataset } from "@/api/datasets";
import type { FetchDataResponse } from "@/api/tools";
import type { PreparedUpload } from "@/components/Panels/Upload/types";
import type { UploadedDataset } from "@/components/Panels/Upload/uploadModalTypes";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { useConfig } from "@/composables/config";
import type { LibraryDatasetUploadItem, NewUploadItem } from "@/composables/upload/uploadItemTypes";
import { errorMessageAsString } from "@/utils/simple-error";
import { uploadDatasets } from "@/utils/upload";

interface UploadResponseData {
    id: string;
    name?: string;
    label?: string;
    hid?: number;
    src?: string;
}

interface TrackedUpload<T extends NewUploadItem = NewUploadItem> {
    item: T;
    id: string;
}

function isUploadResponseData(value: unknown): value is UploadResponseData {
    if (!value || typeof value !== "object") {
        return false;
    }
    // At minimum, check that it has an 'id' property which is what we actually need
    return "id" in value && typeof value.id === "string";
}

function isLibraryDatasetUpload(item: NewUploadItem): item is LibraryDatasetUploadItem {
    return item.uploadMode === "data-library";
}

function isTrackedLibraryUpload(tracked: TrackedUpload): tracked is TrackedUpload<LibraryDatasetUploadItem> {
    return isLibraryDatasetUpload(tracked.item);
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

    /**
     * Update progress for multiple tracked uploads.
     */
    const updateTrackedProgress = (ids: string[], percentage: number): void => {
        ids.forEach((id) => uploadState.updateProgress(id, percentage));
    };

    /**
     * Mark tracked uploads as completed.
     */
    const markTrackedCompleted = (ids: string[]): void => {
        ids.forEach((id) => {
            uploadState.updateProgress(id, 100);
            uploadState.setStatus(id, "completed");
        });
    };

    /**
     * Mark an error for all tracked uploads.
     */
    const markTrackedError = (trackedUploads: TrackedUpload[], message: string): void => {
        trackedUploads.forEach((tracked) => uploadState.setError(tracked.id, message));
    };

    /**
     * Initialize tracked uploads for the given upload items.
     */
    const initializeUploads = (prepared: PreparedUpload): TrackedUpload[] => {
        if (!prepared.uploadItems) {
            return [];
        }

        const trackedUploads = prepared.uploadItems.map((item) => ({
            item,
            id: uploadState.addUploadItem(item),
        }));

        trackedUploads.forEach((tracked) => uploadState.setStatus(tracked.id, "uploading"));

        return trackedUploads;
    };

    /**
     * Separate API uploads from library uploads.
     */
    const filterUploadsByType = (
        trackedUploads: TrackedUpload[],
    ): { apiIds: string[]; libraryUploads: TrackedUpload<LibraryDatasetUploadItem>[] } => {
        const apiIds: string[] = [];
        const libraryUploads: TrackedUpload<LibraryDatasetUploadItem>[] = [];

        trackedUploads.forEach((tracked) => {
            if (isTrackedLibraryUpload(tracked)) {
                libraryUploads.push(tracked);
            } else {
                apiIds.push(tracked.id);
            }
        });

        return { apiIds, libraryUploads };
    };

    /**
     * Process API-based uploads with progress tracking.
     */
    const processApiUploads = async (
        prepared: PreparedUpload,
        apiIds: string[],
        datasets: UploadedDataset[],
        trackedUploads: TrackedUpload[],
        onProgress?: (percentage: number) => void,
    ): Promise<void> => {
        if (prepared.apiItems.length === 0) {
            return;
        }

        return new Promise<void>((resolve, reject) => {
            uploadDatasets(prepared.apiItems, {
                chunkSize: galaxyConfig.value.chunk_upload_size as number,
                success: (response) => {
                    markTrackedCompleted(apiIds);
                    datasets.push(...datasetsFromResponse(response));
                    resolve();
                },
                error: (uploadError) => {
                    markTrackedError(trackedUploads, errorMessageAsString(uploadError));
                    reject(uploadError);
                },
                progress: (percentage) => {
                    onProgress?.(percentage);
                    updateTrackedProgress(apiIds, percentage);
                },
            });
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
            markTrackedCompleted([tracked.id]);
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
        const trackedUploads = initializeUploads(prepared);
        const { apiIds, libraryUploads } = filterUploadsByType(trackedUploads);

        await processApiUploads(prepared, apiIds, datasets, trackedUploads, onProgress);
        await processLibraryUploads(libraryUploads, historyId, datasets);

        return datasets;
    }

    return { submitPreparedUpload };
}
