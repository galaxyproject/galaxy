import type { FileDataElement, HdasUploadTarget, PastedDataElement, UrlDataElement } from "@/api/tools";
import { urlDataElement } from "@/api/tools";
import { errorMessageAsString } from "@/utils/simple-error";
import { uploadSubmit } from "@/utils/upload-submit.js";

import type { NewUploadItem } from "./uploadState";
import { useUploadState } from "./uploadState";

/**
 * Extracts hash value by function name from upload item hashes.
 */
function getHashValue(item: NewUploadItem, hashFunction: string) {
    return item.hashes?.find((h) => h.hash_function === hashFunction)?.hash_value;
}

/**
 * Builds common hash properties for upload elements.
 */
function buildHashProperties(item: NewUploadItem) {
    return {
        MD5: getHashValue(item, "MD5"),
        "SHA-1": getHashValue(item, "SHA-1"),
        "SHA-256": getHashValue(item, "SHA-256"),
        "SHA-512": getHashValue(item, "SHA-512"),
    };
}

/**
 * Builds common properties shared across all upload element types.
 */
function buildCommonProperties(item: NewUploadItem) {
    return {
        name: item.name,
        dbkey: item.dbkey,
        ext: item.extension,
        space_to_tab: item.spaceToTab,
        to_posix_lines: item.toPosixLines,
        auto_decompress: true,
        deferred: item.deferred,
        hashes: item.hashes,
        ...buildHashProperties(item),
    };
}

/**
 * Builds the upload element based on upload item type.
 */
function buildUploadElement(item: NewUploadItem): FileDataElement | PastedDataElement | UrlDataElement {
    const common = buildCommonProperties(item);

    switch (item.uploadMode) {
        case "local-file":
            return {
                ...common,
                src: "files",
            };
        case "paste-content":
            return {
                ...common,
                src: "pasted",
                paste_content: item.content,
            };
        case "paste-links": {
            const baseElement = urlDataElement(item.name, item.url);
            return {
                ...baseElement,
                ...common,
            };
        }
    }
}

/**
 * Builds the upload payload for submission based on upload item type.
 */
function buildUploadPayload(item: NewUploadItem) {
    const element = buildUploadElement(item);

    const target: HdasUploadTarget = {
        auto_decompress: true,
        destination: { type: "hdas" },
        elements: [element] as unknown as HdasUploadTarget["elements"],
    };

    const data = {
        history_id: item.targetHistoryId,
        targets: [target],
        auto_decompress: true,
        ...setFiles(item),
    };

    return { data, isComposite: false };
}

function setFiles(item: NewUploadItem) {
    if (item.uploadMode === "local-file" && item.fileData) {
        return { files: [item.fileData] };
    }
    return { files: [] };
}

/**
 * Composable for managing upload queue and processing.
 * Provides methods to enqueue different types of uploads and track their progress.
 */
export function useUploadService() {
    const uploadState = useUploadState();
    const queue: string[] = [];
    let processing = false;

    /**
     * Processes the next upload in the queue.
     * Handles upload submission with progress tracking and error handling.
     */
    async function processNext() {
        if (processing || queue.length === 0) {
            return;
        }

        const id = queue.shift()!;
        processing = true;

        const item = uploadState.activeItems.value.find((i) => i.id === id);
        if (!item) {
            processing = false;
            return processNext();
        }

        try {
            uploadState.setStatus(id, "uploading");
            const { data, isComposite } = buildUploadPayload(item);

            await new Promise<void>((resolve) => {
                uploadSubmit({
                    data,
                    isComposite,
                    progress: (p: number) => uploadState.updateProgress(id, p),
                    success: () => {
                        uploadState.updateProgress(id, 100);
                        resolve();
                    },
                    error: (e: unknown) => {
                        uploadState.setError(id, errorMessageAsString(e));
                        resolve();
                    },
                });
            });
        } catch (e) {
            uploadState.setError(id, errorMessageAsString(e));
        } finally {
            processing = false;
            processNext();
        }
    }

    /**
     * Enqueues items and starts processing.
     * @param items - Array of upload items to enqueue
     * @returns Array of upload IDs
     */
    function enqueue(items: NewUploadItem[]) {
        const ids = items.map((item) => uploadState.addUploadItem(item));
        queue.push(...ids);
        processNext();
        return ids;
    }

    return {
        enqueue,
        /** Removes all completed uploads from the state */
        clearCompleted: () => uploadState.clearCompleted(),
        /** Clears all uploads from the state */
        clearAll: () => uploadState.clearAll(),
        /** Access to upload state for UI components */
        state: uploadState,
    };
}
