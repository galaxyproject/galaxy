import { copyDataset } from "@/api/datasets";
import type { PreparedUpload } from "@/components/Panels/Upload/types";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { useConfig } from "@/composables/config";
import { registerUploadController, unregisterUploadController } from "@/composables/upload/uploadCancellation";
import type { LibraryDatasetUploadItem, UploadedDataset } from "@/composables/upload/uploadItemTypes";
import { datasetsFromFetchResponse } from "@/composables/upload/uploadResponse";
import type { InitializedUploads, TrackedUpload } from "@/composables/upload/uploadTracking";
import {
    initializeTrackedUploads,
    markTrackedCompleted,
    markTrackedError,
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
     *
     * `signal` cancels the whole submission at once (used for collection/composite
     * uploads, which must be submitted atomically). `signals` provides one AbortSignal
     * per standalone item — cancelling one item skips it while the rest still upload.
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

        return new Promise<void>((resolve, reject) => {
            const config: UploadDatasetsConfig = {
                chunkSize,
                preferredObjectStoreId: targetObjectStoreId,
                success: (response) => {
                    const uploadedDatasets = datasetsFromFetchResponse(response);

                    // In per-file mode, only items whose signals are not aborted
                    // at success time were actually uploaded and should be marked completed.
                    const completedIds = signals ? apiIds.filter((_, i) => !signals[i]?.aborted) : apiIds;
                    markTrackedCompleted(uploadState, completedIds);
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
                    // In atomic mode, if the signal was aborted the cancellation
                    // is the expected outcome — resolve silently. In per-file mode
                    // the error callback is already suppressed for aborted files
                    // inside uploadFilesViaTus, so a genuine error here should be
                    // treated as a real failure.
                    if (!signals && signal?.aborted) {
                        resolve();
                        return;
                    }

                    const errorMessage = errorMessageAsString(uploadError);

                    markTrackedError(uploadState, trackedUploads, errorMessage);
                    if (batchId) {
                        uploadState.setBatchError(batchId, errorMessage);
                    }
                    reject(uploadError);
                },
                progress: (percentage) => {
                    onProgress?.(percentage);
                },
                uploadIds: apiIds,
                perFileProgress: (fileId, percentage) => {
                    uploadState.updateProgress(fileId, percentage);
                },
            };

            if (prepared.collectionConfig && directCollectionCreation) {
                uploadCollectionDatasets(
                    prepared.apiItems,
                    {
                        collectionName: prepared.collectionConfig.name,
                        collectionType: prepared.collectionConfig.type,
                    },
                    { ...config, signal },
                );
            } else {
                uploadDatasets(prepared.apiItems, {
                    ...config,
                    composite: prepared.uploadOptions?.composite,
                    compositeName: prepared.uploadOptions?.compositeName,
                    signal,
                    signals,
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
     * `signal` cancels all remaining library uploads at once (collection batches).
     * `signals` provides one AbortSignal per item — a cancelled item is skipped, and the
     * rest are still copied.
     *
     * @param libraryUploads - Array of tracked library upload items to process
     * @param historyId - The target history ID to copy datasets into
     * @param datasets - Array to collect successfully copied datasets
     * @param options - Optional batch ID and cancellation signals
     * @returns Promise that resolves when all library uploads complete
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
     * Registers cancellation controllers for an upload submission, runs the
     * upload process, and guarantees cleanup.
     *
     * In atomic mode a single `AbortController` is shared by all items (and the
     * optional batch). In per-file mode each item gets its own controller so
     * cancelling one item doesn't affect the others.
     *
     * @param fn - Receives a `CancellationConfig` (either `signal` or `signals`)
     *   where `signals` is positional, aligned with `allUploadIds`.
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
