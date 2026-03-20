/**
 * Upload item type definitions for the upload queue.
 * These types represent items in various stages of the upload lifecycle.
 */

import type { HistoryContentSource } from "@/api/datasets";
import type { FetchDatasetHash } from "@/api/tools";
import type { UploadMethod } from "@/components/Panels/Upload/types";

/** Upload lifecycle status */
export type UploadStatus = "queued" | "uploading" | "processing" | "completed" | "error";

/** Common properties shared by all upload item types */
interface UploadItemCommon {
    uploadMode: UploadMethod;
    name: string;
    size: number;
    targetHistoryId: string;
    dbkey: string;
    extension: string;
    spaceToTab: boolean;
    toPosixLines: boolean;
    deferred: boolean;
    hashes?: FetchDatasetHash[];
}

/** Upload item from a local file */
export interface LocalFileUploadItem extends UploadItemCommon {
    uploadMode: "local-file";
    /** File handle (not persisted in localStorage) */
    fileData?: File;
}

/** Upload item from pasted text content */
export interface PastedContentUploadItem extends UploadItemCommon {
    uploadMode: "paste-content";
    content: string;
}

/** Upload item from a URL */
export interface UrlUploadItem extends UploadItemCommon {
    uploadMode: "paste-links";
    url: string;
}

/** Upload item from a remote file */
export interface RemoteFileUploadItem extends UploadItemCommon {
    uploadMode: "remote-files";
    url: string;
}

/**
 * A single serializable slot in a composite upload.
 * File objects are not serializable, so `file` is marked optional and lost on refresh.
 */
export interface CompositeSlotQueueItem {
    /** Machine name of the slot */
    slotName: string;
    /** Source discriminant mirroring ApiUploadItem.src */
    src: "files" | "url" | "paste";
    /** Local file (not persisted in localStorage) */
    file?: File;
    /** Remote URL (present when src === "url") */
    url?: string;
    /** Pasted content (present when src === "paste") */
    content?: string;
    /** Whether this slot is optional */
    optional: boolean;
    /**
     * Human-readable description of the slot from the datatype definition.
     * Absent when the datatype provides no description.
     */
    description?: string;
    /**
     * Display label for the source: the local file name, remote file name, URL string,
     * or "Pasted content" for paste slots. Used in the progress panel slot breakdown.
     */
    displayName?: string;
    /**
     * Size in bytes of the slot content, when known at queue time.
     */
    fileSize?: number;
}

/** Upload item for a composite datatype (multiple files → one HDA) */
export interface CompositeFileUploadItem extends UploadItemCommon {
    uploadMode: "composite-file";
    /** Component file slots */
    slots: CompositeSlotQueueItem[];
}

/** Upload item from a Data Library dataset */
export interface LibraryDatasetUploadItem extends UploadItemCommon {
    uploadMode: "data-library";
    /** ID of the library containing this dataset */
    libraryId: string;
    /** ID of the folder containing this dataset */
    folderId: string;
    /** LibraryDatasetDatasetAssociation ID */
    lddaId: string;
    /** API URL for dataset retrieval */
    url: string;
}

/** Union of all new upload item types (before state tracking is added) */
export type NewUploadItem =
    | LocalFileUploadItem
    | PastedContentUploadItem
    | UrlUploadItem
    | RemoteFileUploadItem
    | LibraryDatasetUploadItem
    | CompositeFileUploadItem;

/** Internal state tracking for an upload */
export interface UploadState {
    id: string;
    status: UploadStatus;
    progress: number;
    error?: string;
    createdAt: number;
    /** Optional reference to parent batch */
    batchId?: string;
}

/** Upload item with state tracking (used in active upload queue) */
export type UploadItem = NewUploadItem & UploadState;

/** Sources returned for uploaded history contents. */
export type UploadedDatasetSource = Extract<HistoryContentSource, "hda" | "hdca">;

/**
 * Validates a UI upload item before submission.
 * Returns an error message if invalid, undefined if valid.
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
        case "remote-files":
            if (!item.url || item.url.trim().length === 0) {
                return `No URL provided for "${item.name}"`;
            }
            break;

        case "data-library":
            if (!item.lddaId) {
                return `No library dataset ID provided for "${item.name}"`;
            }
            break;

        default:
            return `Unknown upload mode: ${(item as NewUploadItem).uploadMode}`;
    }
    return undefined;
}

/**
 * Represents a dataset that was successfully uploaded.
 */
export interface UploadedDataset {
    /** Unique identifier for the dataset. */
    id: string;
    /** Display name of the dataset. */
    name: string;
    /** History item ID (sequential index). */
    hid?: number;
    /** Type of dataset: history dataset (hda) or history dataset collection (hdca). */
    src: UploadedDatasetSource;
}
