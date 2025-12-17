/**
 * Utility functions for mapping upload method items to upload queue items.
 * These mappers convert component-specific item types to standardized upload queue format.
 */

import type { LocalFileItem, PasteContentItem, PasteUrlItem } from "@/components/Panels/Upload/types/uploadItem";
import type {
    LocalFileUploadItem,
    PastedContentUploadItem,
    UrlUploadItem,
} from "@/components/Panels/Upload/uploadState";

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
        url: item.url,
    };
}
