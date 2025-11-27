/**
 * Upload submission utilities for Galaxy dataset uploads.
 *
 * This module handles the actual submission of upload payloads to the Galaxy API,
 * including TUS chunked uploads for large files.
 */
import { GalaxyApi } from "@/api";
import type { FetchDataPayload, FetchDataResponse } from "@/api/tools";
import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString } from "@/utils/simple-error";

import { createTusUpload, type NamedBlob } from "./tusUpload";
import type { BuildPayloadOptions, UploadItem, UploadPayload } from "./uploadPayload";
import { buildUploadPayload, DEFAULT_FILE_NAME } from "./uploadPayload";

// Re-export types and utilities for consumers
export type { LocalFileUploadItem, PastedContentUploadItem, UploadItem, UrlUploadItem } from "./uploadPayload";
export {
    buildUploadPayload,
    createFileUploadItem,
    createPastedUploadItem,
    createUrlUploadItem,
    DEFAULT_FILE_NAME,
    isGalaxyFileName,
    isUploadableFile,
    parseContentToUploadItems,
    stripGalaxyFilePrefix,
    uploadItemDefaults,
} from "./uploadPayload";

// Legacy compatibility exports (deprecated, for backward compatibility)
export type { LegacyUploadItem } from "./uploadPayload";
export { buildLegacyPayload, fromLegacyUploadItem, fromLegacyUploadItems } from "./uploadPayload";

/**
 * Callback functions for upload lifecycle events.
 */
export interface UploadCallbacks {
    /** Called when upload completes successfully */
    success?: (response: FetchDataResponse) => void;
    /** Called when an error occurs */
    error?: (error: string | Error) => void;
    /** Called with warning messages (currently unused but part of contract) */
    warning?: (message: string) => void;
    /** Called with upload progress percentage (0-100) */
    progress?: (percentage: number) => void;
}

/**
 * Upload payload with optional error message for validation failures.
 */
export interface UploadDataPayload extends UploadPayload {
    /** Optional error message that will cause immediate failure */
    error_message?: string;
}

/**
 * Configuration for upload submission.
 */
export interface UploadSubmitConfig extends UploadCallbacks {
    /** The upload payload data */
    data: UploadDataPayload;
    /** Whether this is a composite upload */
    isComposite?: boolean;
    /** Chunk size for TUS uploads in bytes (default: 10MB) */
    chunkSize?: number;
}

/**
 * Sends the upload payload to the Galaxy API.
 *
 * @param payload - The fetch data payload
 * @param callbacks - Success and error callbacks
 */
export async function sendPayload(payload: FetchDataPayload, callbacks: UploadCallbacks = {}): Promise<void> {
    try {
        const { data, error } = await GalaxyApi().POST("/api/tools/fetch", {
            body: payload,
        });

        if (error) {
            throw new Error(error.err_msg || "Upload request failed");
        }

        callbacks.success?.(data as FetchDataResponse);
    } catch (error) {
        const errorMessage = errorMessageAsString(error);
        callbacks.error?.(errorMessage);
    }
}

/**
 * Submits files for upload to Galaxy.
 * Handles TUS chunked uploads for files and direct payload submission for URLs.
 *
 * @param config - Upload configuration
 */
export async function submitDatasetUpload(config: UploadSubmitConfig): Promise<void> {
    // Set default options
    const {
        data,
        success = () => {},
        error = () => {},
        warning = () => {},
        progress = () => {},
        isComposite = false,
        chunkSize = 10485760, // 10MB default
    } = config;

    // Initial validation
    if (data.error_message) {
        error(data.error_message);
        return;
    }

    const tusEndpoint = `${getAppRoot()}api/upload/resumable_upload/`;
    const callbacks: UploadCallbacks = { success, error, warning, progress };

    // Determine upload path based on data structure
    const hasFiles = data.files && data.files.length > 0;

    if (hasFiles || isComposite) {
        // Upload files via TUS, then submit payload
        await uploadFilesViaTus(data, tusEndpoint, chunkSize, callbacks);
    } else if (data.targets && data.targets.length > 0) {
        // Handle URL or pasted content
        const firstTarget = data.targets[0];

        if (firstTarget && "elements" in firstTarget && firstTarget.elements && firstTarget.elements.length > 0) {
            const firstElement = firstTarget.elements[0];

            if (firstElement && "src" in firstElement) {
                if (firstElement.src === "url") {
                    // Direct URL submission - no TUS upload needed
                    const apiPayload = toApiPayload(data);
                    await sendPayload(apiPayload, callbacks);
                } else if (firstElement.src === "pasted" && "paste_content" in firstElement) {
                    // Convert pasted content to Blob and upload via TUS
                    const pasteContent = String(firstElement.paste_content);
                    const blob = new Blob([pasteContent]) as NamedBlob;
                    blob.name = String(firstElement.name || DEFAULT_FILE_NAME);

                    const filesData: UploadPayload = { ...data, files: [blob] };
                    await uploadFilesViaTus(filesData, tusEndpoint, chunkSize, callbacks);
                }
            }
        }
    }
}

/**
 * Converts UploadPayload to FetchDataPayload for API submission.
 */
function toApiPayload(data: UploadPayload): FetchDataPayload {
    return {
        history_id: data.history_id,
        targets: data.targets,
        auto_decompress: data.auto_decompress,
    };
}

/**
 * Uploads files via TUS protocol, then submits the complete payload.
 */
async function uploadFilesViaTus(
    data: UploadPayload,
    tusEndpoint: string,
    chunkSize: number,
    callbacks: UploadCallbacks,
): Promise<void> {
    const files = data.files || [];

    // Build API payload with TUS session info
    const apiPayload: Record<string, unknown> = {
        history_id: data.history_id,
        targets: data.targets,
        auto_decompress: data.auto_decompress,
    };

    try {
        // Upload each file sequentially via TUS
        for (let index = 0; index < files.length; index++) {
            const file = files[index];
            if (!file) {
                continue;
            }

            const result = await createTusUpload({
                file,
                endpoint: tusEndpoint,
                historyId: data.history_id,
                chunkSize,
                onProgress: callbacks.progress || (() => {}),
                onError: (err: Error) => {
                    callbacks.error?.(err);
                },
            });

            // Add TUS session information to payload
            apiPayload[`files_${index}|file_data`] = {
                session_id: result.sessionId,
                name: result.fileName,
            };
        }

        await sendPayload(apiPayload as FetchDataPayload, callbacks);
    } catch (err) {
        // Ensure error callback is invoked
        if (err instanceof Error) {
            callbacks.error?.(err);
        }
    }
}

/**
 * Configuration for the uploadDatasets function.
 */
export interface UploadDatasetsConfig extends UploadCallbacks, BuildPayloadOptions {
    /** Chunk size for TUS uploads in bytes (default: 10MB) */
    chunkSize?: number;
}

/**
 * Uploads datasets to Galaxy with a simplified API.
 * Combines payload building, TUS file upload, and API submission in one call.
 *
 * @param items - The upload items to process
 * @param config - Upload configuration and callbacks
 *
 * @example
 * ```typescript
 * await uploadDatasets([
 *   createFileUploadItem(file, "history123", { ext: "bed" }),
 *   createUrlUploadItem("https://example.com/data.txt", "history123"),
 * ], {
 *   success: (response) => console.log("Upload complete", response),
 *   error: (err) => console.error("Upload failed", err),
 *   progress: (pct) => console.log(`Progress: ${pct}%`),
 * });
 * ```
 */
export async function uploadDatasets(items: UploadItem[], config: UploadDatasetsConfig = {}): Promise<void> {
    const { composite = false, chunkSize, success, error, warning, progress } = config;

    try {
        // Build the API-ready payload from upload items
        const payload: UploadPayload = buildUploadPayload(items, { composite });

        // Prepare the data for submission
        const data: UploadDataPayload = {
            history_id: payload.history_id,
            targets: payload.targets,
            auto_decompress: payload.auto_decompress,
            files: payload.files,
        };

        // Submit using existing infrastructure
        await submitDatasetUpload({
            data,
            isComposite: composite,
            chunkSize,
            success,
            error,
            warning,
            progress,
        });
    } catch (err) {
        const errorMessage = errorMessageAsString(err);
        config.error?.(errorMessage);
    }
}
