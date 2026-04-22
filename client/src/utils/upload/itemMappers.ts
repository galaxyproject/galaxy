/**
 * Utility functions for mapping upload method items to upload queue items.
 * These mappers convert component-specific item types to standardized upload queue format.
 */

import type {
    CompositeFileItem,
    LibraryDatasetItem,
    LocalFileItem,
    PasteContentItem,
    PasteUrlItem,
    RemoteFileItem,
} from "@/components/Panels/Upload/types/uploadItem";
import type {
    CompositeFileUploadItem,
    CompositeSlotQueueItem,
    LibraryDatasetUploadItem,
    LocalFileUploadItem,
    PastedContentUploadItem,
    RemoteFileUploadItem,
    UrlUploadItem,
} from "@/composables/upload/uploadItemTypes";

/**
 * Maps a local file item to a local file upload item for the upload queue
 */
export function mapToLocalFileUpload(item: LocalFileItem, targetHistoryId: string): LocalFileUploadItem {
    return {
        uploadMode: "local-file" as const,
        name: item.name,
        size: item.file.size,
        targetHistoryId,
        dbkey: item.dbkey,
        extension: item.extension,
        spaceToTab: item.spaceToTab,
        toPosixLines: item.toPosixLines,
        deferred: false,
        fileData: item.file,
    };
}

/**
 * Maps a paste content item to a pasted content upload item for the upload queue
 */
export function mapToPasteContentUpload(item: PasteContentItem, targetHistoryId: string): PastedContentUploadItem {
    return {
        uploadMode: "paste-content" as const,
        name: item.name,
        size: new Blob([item.content]).size,
        targetHistoryId,
        dbkey: item.dbkey,
        extension: item.extension,
        spaceToTab: item.spaceToTab,
        toPosixLines: item.toPosixLines,
        deferred: false,
        content: item.content,
    };
}

/**
 * Maps a paste URL item to a URL upload item for the upload queue
 */
export function mapToPasteUrlUpload(item: PasteUrlItem, targetHistoryId: string): UrlUploadItem {
    return {
        uploadMode: "paste-links" as const,
        name: item.name,
        size: 0,
        targetHistoryId,
        dbkey: item.dbkey,
        extension: item.extension,
        spaceToTab: item.spaceToTab,
        toPosixLines: item.toPosixLines,
        deferred: item.deferred,
        url: item.url.trim(),
    };
}

/**
 * Maps a remote file item to a remote file upload item for the upload queue
 */
export function mapToRemoteFileUpload(item: RemoteFileItem, targetHistoryId: string): RemoteFileUploadItem {
    return {
        uploadMode: "remote-files" as const,
        name: item.name,
        size: item.size,
        targetHistoryId,
        dbkey: item.dbkey,
        extension: item.extension,
        spaceToTab: item.spaceToTab,
        toPosixLines: item.toPosixLines,
        deferred: item.deferred,
        url: item.url,
        hashes: item.hashes,
    };
}

/**
 * Maps a library dataset item to a library dataset upload item for the upload queue
 */
export function mapToLibraryDatasetUpload(item: LibraryDatasetItem, targetHistoryId: string): LibraryDatasetUploadItem {
    return {
        uploadMode: "data-library" as const,
        name: item.name,
        size: item.size,
        targetHistoryId,
        dbkey: "?", // Library datasets use their existing dbkey
        extension: item.extension,
        spaceToTab: false, // Not applicable to library imports
        toPosixLines: false, // Not applicable to library imports
        libraryId: item.libraryId,
        folderId: item.folderId,
        lddaId: item.lddaId,
        url: item.url,
        deferred: false,
    };
}

/**
 * Maps a CompositeFileItem to a CompositeFileUploadItem for the upload queue.
 * Each slot is converted to a serializable CompositeSlotQueueItem; File objects
 * survive in memory but are lost on page refresh (same as local-file uploads).
 */
export function mapToCompositeFileUpload(item: CompositeFileItem, targetHistoryId: string): CompositeFileUploadItem {
    const slots: CompositeSlotQueueItem[] = item.slots.map((slot) => {
        if (slot.mode === "local") {
            return {
                slotName: slot.slotName,
                src: "files" as const,
                file: slot.file,
                optional: slot.optional,
                description: slot.description || undefined,
                displayName: slot.file?.name ?? "Unnamed file",
                fileSize: slot.fileSize,
            };
        } else if (slot.mode === "url") {
            return {
                slotName: slot.slotName,
                src: "url" as const,
                url: slot.url,
                optional: slot.optional,
                description: slot.description || undefined,
                displayName: slot.url,
            };
        } else if (slot.mode === "remote") {
            return {
                slotName: slot.slotName,
                src: "url" as const,
                url: slot.remoteUri,
                optional: slot.optional,
                description: slot.description || undefined,
                displayName: slot.remoteName,
                fileSize: slot.fileSize,
            };
        } else {
            return {
                slotName: slot.slotName,
                src: "paste" as const,
                content: slot.content,
                optional: slot.optional,
                description: slot.description || undefined,
                displayName: "Pasted content",
                fileSize: new Blob([slot.content]).size,
            };
        }
    });

    const totalSize = slots.reduce((sum, s) => sum + (s.fileSize ?? 0), 0);
    const displayName = item.name.trim() || `Unnamed ${item.extension} composite`;

    return {
        uploadMode: "composite-file" as const,
        name: displayName,
        size: totalSize,
        targetHistoryId,
        dbkey: item.dbkey,
        extension: item.extension,
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        slots,
    };
}
