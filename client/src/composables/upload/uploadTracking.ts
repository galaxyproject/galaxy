import type { UploadStateTrackingApi } from "@/components/Panels/Upload/uploadState";

import type { UploadCollectionConfig } from "./collectionTypes";
import type { LibraryDatasetUploadItem, NewUploadItem } from "./uploadItemTypes";

/**
 * Represents an upload item being tracked through its lifecycle.
 * @template T - The specific type of upload item (NewUploadItem or subtypes)
 */
export interface TrackedUpload<T extends NewUploadItem = NewUploadItem> {
    /** The upload item configuration */
    item: T;
    /** Unique identifier for this tracked upload */
    id: string;
}

/**
 * Result of initializing tracked uploads.
 * Contains the tracked uploads and optional batch ID for collection uploads.
 */
export interface InitializedUploads {
    /** Array of tracked uploads created from the input items */
    trackedUploads: TrackedUpload[];
    /** Batch ID if uploads were initialized as part of a collection */
    batchId?: string;
}

/**
 * Options for initializing tracked uploads.
 */
interface InitializeTrackedUploadsOptions {
    /** Collection configuration if uploads should be part of a collection */
    collectionConfig?: UploadCollectionConfig;
    /** Whether to use direct HDCA creation (no separate collection creation step) */
    directCreation?: boolean;
    /** Whether to immediately start uploading (sets status to "uploading") */
    startUploading?: boolean;
}

/**
 * Initializes tracked uploads for a set of upload items.
 * Creates upload items in the upload state and optionally creates a collection batch.
 *
 * @param uploadState - Upload state tracking API
 * @param items - Upload items to initialize (file, URL, paste uploads, etc.)
 * @param options - Initialization options
 * @returns Initialized uploads with tracked items and optional batch ID
 */
export function initializeTrackedUploads(
    uploadState: UploadStateTrackingApi,
    items: NewUploadItem[] | undefined,
    options: InitializeTrackedUploadsOptions = {},
): InitializedUploads {
    if (!items || items.length === 0) {
        return { trackedUploads: [] };
    }

    const batchId = options.collectionConfig
        ? uploadState.addBatch(options.collectionConfig, [], options.directCreation ?? false)
        : undefined;

    const trackedUploads = items.map((item) => ({
        item,
        id: uploadState.addUploadItem(item, batchId),
    }));

    if (batchId) {
        const batch = uploadState.getBatch(batchId);
        if (batch) {
            batch.uploadIds = trackedUploads.map((tracked) => tracked.id);
        }
    }

    if (options.startUploading) {
        trackedUploads.forEach((tracked) => uploadState.setStatus(tracked.id, "uploading"));
    }

    return { trackedUploads, batchId };
}

/**
 * Updates the progress of multiple tracked uploads.
 *
 * @param uploadState - Upload state tracking API
 * @param ids - Upload item IDs to update
 * @param percentage - Progress percentage (0-100)
 */
export function updateTrackedProgress(uploadState: UploadStateTrackingApi, ids: string[], percentage: number): void {
    ids.forEach((id) => uploadState.updateProgress(id, percentage));
}

/**
 * Marks multiple tracked uploads as completed.
 * Sets progress to 100% and status to "completed".
 */
export function markTrackedCompleted(uploadState: UploadStateTrackingApi, ids: string[]): void {
    ids.forEach((id) => {
        uploadState.updateProgress(id, 100);
        uploadState.setStatus(id, "completed");
    });
}

/**
 * Marks multiple tracked uploads as failed with an error message.
 *
 * @param uploadState - Upload state tracking API
 * @param trackedUploads - Tracked uploads to mark as failed
 * @param message - Error message describing the failure
 */
export function markTrackedError(
    uploadState: UploadStateTrackingApi,
    trackedUploads: Array<Pick<TrackedUpload, "id">>,
    message: string,
): void {
    trackedUploads.forEach((tracked) => uploadState.setError(tracked.id, message));
}

function isTrackedLibraryUpload(tracked: TrackedUpload): tracked is TrackedUpload<LibraryDatasetUploadItem> {
    return tracked.item.uploadMode === "data-library";
}

/**
 * Splits tracked uploads by their type (API uploads vs library uploads).
 * Useful for handling different upload modes after initialization.
 *
 * @param trackedUploads - Tracked uploads to split
 * @returns Object containing arrays of API upload IDs and library uploads
 */
export function splitTrackedUploadsByType(trackedUploads: TrackedUpload[]): {
    apiIds: string[];
    libraryUploads: TrackedUpload<LibraryDatasetUploadItem>[];
} {
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
}
