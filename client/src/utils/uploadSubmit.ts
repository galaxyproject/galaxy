import { GalaxyApi } from "@/api";
import type { FetchDataPayload, FetchDataResponse } from "@/api/tools";
import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString } from "@/utils/simple-error";

import { createTusUpload, type NamedBlob, type UploadableFile } from "./tusUpload";

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
 * Extended FetchDataPayload with upload-specific properties.
 */
export interface UploadDataPayload extends FetchDataPayload {
    /** Array of files to upload via TUS */
    files?: UploadableFile[];
    /** Optional error message that will cause immediate failure */
    error_message?: string;
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
                    await sendPayload(data, callbacks);
                } else if (firstElement.src === "pasted" && "paste_content" in firstElement) {
                    // Convert pasted content to Blob and upload via TUS
                    const pasteContent = String(firstElement.paste_content);
                    const blob = new Blob([pasteContent]) as NamedBlob;
                    blob.name = String(firstElement.name || "default");

                    const filesData = { ...data, files: [blob] };
                    await uploadFilesViaTus(filesData, tusEndpoint, chunkSize, callbacks);
                }
            }
        }
    }
}

/**
 * Uploads files via TUS protocol, then submits the complete payload.
 *
 * @param data - The upload data containing files
 * @param tusEndpoint - The TUS upload endpoint URL
 * @param chunkSize - Size of upload chunks in bytes
 * @param callbacks - Upload lifecycle callbacks
 */
async function uploadFilesViaTus(
    data: UploadDataPayload,
    tusEndpoint: string,
    chunkSize: number,
    callbacks: UploadCallbacks,
): Promise<void> {
    const files = data.files || [];

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
            data[`files_${index}|file_data` as keyof typeof data] = {
                session_id: result.sessionId,
                name: result.fileName,
            };
        }

        // Remove files array and submit the payload
        delete data.files;
        await sendPayload(data, callbacks);
    } catch (err) {
        // Error already handled by callbacks in createTusUpload
        // But ensure error callback is invoked if not already done
        if (err instanceof Error) {
            callbacks.error?.(err);
        }
    }
}
