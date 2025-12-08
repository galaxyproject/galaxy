/**
 * Upload queue composable for managing dataset uploads to Galaxy.
 *
 * This composable provides a queue-based upload system that:
 * - Converts UI upload items to API-ready format
 * - Processes uploads sequentially with progress tracking
 * - Persists upload state for UI monitoring
 */
import type { NewUploadItem } from "@/components/Panels/Upload/uploadState";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { errorMessageAsString } from "@/utils/simple-error";
import type { UploadItem } from "@/utils/upload";
import { createFileUploadItem, createPastedUploadItem, createUrlUploadItem, uploadDatasets } from "@/utils/upload";

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
    let processing = false;

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

            await uploadDatasets([uploadItem], {
                progress: (percentage) => uploadState.updateProgress(id, percentage),
                success: () => uploadState.updateProgress(id, 100),
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
     * @returns Array of upload IDs for tracking
     */
    function enqueue(items: NewUploadItem[]): string[] {
        const ids = items.map((item) => uploadState.addUploadItem(item));
        queue.push(...ids);
        processNext();
        return ids;
    }

    return {
        /** Enqueue items for upload */
        enqueue,
        /** Removes all completed uploads from the state */
        clearCompleted: () => uploadState.clearCompleted(),
        /** Clears all uploads from the state */
        clearAll: () => uploadState.clearAll(),
        /** Access to upload state for UI components */
        state: uploadState,
    };
}
