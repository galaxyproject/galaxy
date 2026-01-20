/**
 * Upload item type definitions for the upload queue.
 * These types represent items in various stages of the upload lifecycle.
 */

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
    | LibraryDatasetUploadItem;

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
