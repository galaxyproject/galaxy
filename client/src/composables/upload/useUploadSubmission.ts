import { copyDataset } from "@/api/datasets";
import type { PreparedUpload } from "@/components/Panels/Upload/types";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { useConfig } from "@/composables/config";
import { registerUploadController, unregisterUploadController } from "@/composables/upload/uploadCancellation";
import type { LibraryDatasetUploadItem, UploadedDataset } from "@/composables/upload/uploadItemTypes";
import { datasetCollectionsFromFetchResponse, datasetsFromFetchResponse } from "@/composables/upload/uploadResponse";
import type { InitializedUploads, TrackedUpload } from "@/composables/upload/uploadTracking";
import {
    buildDatasetIdMapping,
    initializeTrackedUploads,
    markTrackedError,
    markTrackedProcessing,
    resolveDirectCollectionResult,
    splitTrackedUploadsByType,
} from "@/composables/upload/uploadTracking";
import { useUploadBatchOperations } from "@/composables/upload/useUploadBatchOperations";
import { errorMessageAsString } from "@/utils/simple-error";
import { type CancellationConfig, DEFAULT_CHUNK_SIZE, type UploadDatasetsConfig } from "@/utils/upload";
import { isFetchApiCompatible, uploadCollectionDatasets, uploadDatasets } from "@/utils/upload";

/** Shared cancellation and batch-tracking options for upload processing functions. */
interface UploadProcessingOptions extends CancellationConfig {
    /** Batch ID for collection upload tracking. */
    batchId?: string;
}

/** Options for {@link processApiUploads}. */
interface ProcessApiUploadsOptions extends UploadProcessingOptions {
    /** Whether the upload uses direct HDCA collection creation. */
    directCollectionCreation?: boolean;
    /** Optional callback for aggregate progress updates (0–100). */
    onProgress?: (percentage: number) => void;
    /** Optional preferred object store ID for uploaded datasets. */
    targetObjectStoreId?: string;
}

/** Submits a prepared upload to the Galaxy API. Processing items resolve via the monitor store. */
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

    function addHdaDatasetsToBatch(batchId: string | undefined, hdaDatasets: UploadedDataset[]): void {
        if (batchId) {
            hdaDatasets.forEach((dataset) => uploadState.addBatchDatasetId(batchId, dataset.id));
        }
    }

    /** Library items copy instead of uploading, so they cannot use direct collection creation. */
    function isDirectCollectionCreation(prepared: PreparedUpload): boolean {
        return Boolean(prepared.collectionConfig && prepared.uploadItems?.every(isFetchApiCompatible));
    }

    /**
     * Uploads file-based items, tracking progress in the upload state store.
     *
     * `signal` cancels an atomic submission at once; `signals` carries one
     * AbortSignal per standalone item.
     */
    async function processApiUploads(
        prepared: PreparedUpload,
        apiIds: string[],
        datasets: UploadedDataset[],
        trackedUploads: TrackedUpload[],
        options: ProcessApiUploadsOptions,
    ): Promise<void> {
        const { batchId, directCollectionCreation, onProgress, targetObjectStoreId, signal, signals } = options;

        if (prepared.apiItems.length === 0) {
            return;
        }

        const configuredChunkSize = Number(galaxyConfig.value.chunk_upload_size);
        const chunkSize = configuredChunkSize > 0 ? configuredChunkSize : DEFAULT_CHUNK_SIZE;

        const config: UploadDatasetsConfig = {
            chunkSize,
            preferredObjectStoreId: targetObjectStoreId,
            success: (response) => {
                const uploadedDatasets = datasetsFromFetchResponse(response);
                const completedIds = signals ? apiIds.filter((_, i) => !signals[i]?.aborted) : apiIds;

                if (batchId && directCollectionCreation) {
                    // Items go to processing; the HDCA resolves via monitoring.
                    resolveDirectCollectionResult(uploadState, batchId, completedIds, response);

                    datasets.push(...uploadedDatasets, ...datasetCollectionsFromFetchResponse(response));
                    return;
                }

                const hdaDatasets = uploadedDatasets.filter((dataset) => dataset.src === "hda");

                const datasetIdsByUploadId = buildDatasetIdMapping(completedIds, hdaDatasets);
                markTrackedProcessing(uploadState, completedIds, datasetIdsByUploadId);

                datasets.push(...uploadedDatasets);
                addHdaDatasetsToBatch(batchId, hdaDatasets);
            },
            error: (uploadError) => {
                if (!signals && signal?.aborted) {
                    return;
                }

                const errorMessage = errorMessageAsString(uploadError);

                markTrackedError(uploadState, trackedUploads, errorMessage);
                if (batchId) {
                    uploadState.setBatchError(batchId, errorMessage);
                }
                throw uploadError instanceof Error ? uploadError : new Error(errorMessage);
            },
            progress: (percentage) => {
                onProgress?.(percentage);
            },
            uploadIds: apiIds,
            perFileProgress: (fileId, percentage) => {
                uploadState.updateProgress(fileId, percentage);
            },
        };

        try {
            if (prepared.collectionConfig && directCollectionCreation) {
                await uploadCollectionDatasets(
                    prepared.apiItems,
                    {
                        collectionName: prepared.collectionConfig.name,
                        collectionType: prepared.collectionConfig.type,
                    },
                    { ...config, signal },
                );
            } else {
                await uploadDatasets(prepared.apiItems, {
                    ...config,
                    composite: prepared.uploadOptions?.composite,
                    compositeName: prepared.uploadOptions?.compositeName,
                    signal,
                    signals,
                });
            }
        } catch (error) {
            if (signal?.aborted) {
                return;
            }
            throw error;
        }
    }

    /**
     * Copies library datasets into the history.
     *
     * `signal` cancels remaining copies at once; `signals` carries one
     * AbortSignal per item.
     *
     * @param libraryUploads - Tracked library uploads to process
     * @param historyId - Target history ID
     * @param datasets - Collects successfully copied datasets
     */
    async function processLibraryUploads(
        libraryUploads: TrackedUpload<LibraryDatasetUploadItem>[],
        historyId: string,
        datasets: UploadedDataset[],
        options: UploadProcessingOptions = {},
    ): Promise<void> {
        const { batchId, signal, signals } = options;

        for (const [index, tracked] of libraryUploads.entries()) {
            const itemSignal = signals?.[index] ?? signal;
            if (itemSignal?.aborted) {
                continue;
            }
            uploadState.updateProgress(tracked.id, 50);
            let copied;
            try {
                copied = await copyDataset(tracked.item.lddaId, historyId, "dataset", "library", itemSignal);
            } catch (err) {
                if (itemSignal?.aborted) {
                    continue;
                }
                throw err;
            }
            if (copied && "id" in copied && copied.id) {
                const copiedName =
                    "name" in copied && typeof copied.name === "string" ? copied.name : tracked.item.name;
                const copiedHid = "hid" in copied && typeof copied.hid === "number" ? copied.hid : undefined;

                const produced: UploadedDataset = {
                    id: copied.id,
                    name: copiedName,
                    hid: copiedHid,
                    src: "hda",
                };
                datasets.push(produced);
                addHdaDatasetsToBatch(batchId, [produced]);
            }
            const datasetIds = copied && "id" in copied && copied.id ? [copied.id] : [];
            markTrackedProcessing(
                uploadState,
                [tracked.id],
                new Map(datasetIds.length > 0 ? [[tracked.id, datasetIds]] : []),
            );
        }
    }

    /**
     * Runs the upload with registered cancellation controllers, then unregisters.
     * Atomic mode shares one controller; per-file mode gives each item its own.
     */
    async function withCancellation(
        allUploadIds: string[],
        batchId: string | undefined,
        isAtomic: boolean,
        fn: (cancellation: CancellationConfig) => Promise<void>,
    ): Promise<void> {
        if (isAtomic) {
            const controller = new AbortController();
            registerUploadController(allUploadIds, batchId, controller);
            try {
                await fn({ signal: controller.signal });
            } finally {
                unregisterUploadController(allUploadIds, batchId);
            }
            return;
        }

        const controllers = new Map(allUploadIds.map((id) => [id, new AbortController()]));
        controllers.forEach((controller, id) => registerUploadController([id], undefined, controller));
        try {
            const signalById = new Map(allUploadIds.map((id) => [id, controllers.get(id)?.signal]));
            await fn({ signals: allUploadIds.map((id) => signalById.get(id)) });
        } finally {
            controllers.forEach((_controller, id) => unregisterUploadController([id], undefined));
        }
    }

    /** Submits a prepared upload; `onProgress` mirrors progress to the caller. */
    async function submitPreparedUpload(
        historyId: string,
        prepared: PreparedUpload,
        onProgress?: (percentage: number) => void,
        targetObjectStoreId?: string,
    ): Promise<UploadedDataset[]> {
        const datasets: UploadedDataset[] = [];
        const directCollectionCreation = isDirectCollectionCreation(prepared);
        const { trackedUploads, batchId } = initializeUploads(prepared);
        const { apiIds, libraryUploads } = splitTrackedUploadsByType(trackedUploads);
        const allUploadIds = trackedUploads.map((t) => t.id);

        const isAtomic = Boolean(batchId) || Boolean(prepared.uploadOptions?.composite);

        await withCancellation(allUploadIds, batchId, isAtomic, async (cancellation) => {
            const { signal } = cancellation;

            if (isAtomic) {
                await processApiUploads(prepared, apiIds, datasets, trackedUploads, {
                    batchId,
                    directCollectionCreation,
                    onProgress,
                    targetObjectStoreId,
                    signal,
                });
                await processLibraryUploads(libraryUploads, historyId, datasets, {
                    batchId,
                    signal,
                });

                if (prepared.collectionConfig && !directCollectionCreation && !signal?.aborted) {
                    await uploadBatchOperations.createCollection(batchId!, signal);
                }
            } else {
                const { signals } = cancellation;
                const signalByUploadId = new Map(allUploadIds.map((id, i) => [id, signals?.[i]]));
                const apiSignals = apiIds.map((id) => signalByUploadId.get(id));
                const librarySignals = libraryUploads.map((t) => signalByUploadId.get(t.id));

                await Promise.all([
                    processApiUploads(prepared, apiIds, datasets, trackedUploads, {
                        directCollectionCreation,
                        onProgress,
                        targetObjectStoreId,
                        signals: apiSignals,
                    }),
                    processLibraryUploads(libraryUploads, historyId, datasets, {
                        signals: librarySignals,
                    }),
                ]);
            }
        });

        return datasets;
    }

    return { submitPreparedUpload };
}
