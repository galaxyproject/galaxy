/**
 * Upload payload builder for Galaxy dataset uploads.
 *
 * This module builds API-ready payloads for the /api/tools/fetch endpoint.
 * All types use API naming conventions directly (dbkey, ext, space_to_tab, etc.)
 * to avoid unnecessary transformation layers.
 */
import type {
    ApiDataElement,
    CompositeDataElement,
    FetchDatasetHash,
    FileDataElement,
    HdasUploadTarget,
    PastedDataElement,
    UrlDataElement,
} from "@/api/tools";
import type { UploadRowModel } from "@/components/Upload/model";

import type { FileStream, UploadableFile } from "./tusUpload";
import { isUrl } from "./url";

/** Default file name used when no name is provided */
export const DEFAULT_FILE_NAME = "New File";

/** Regex pattern for Galaxy-formatted file names (e.g., "Galaxy5-[FileName].bed") */
const GALAXY_FILE_PATTERN = /Galaxy\d+-\[(.*?)\](\..+)/;

/**
 * Common properties shared by all upload item types.
 * Uses API naming conventions directly.
 */
interface UploadItemCommon {
    /** Display name for the upload item */
    name: string;
    /** File size in bytes */
    size: number;
    /** Target history ID for the upload */
    historyId: string;
    /** Genome build / database key */
    dbkey: string;
    /** File type extension */
    ext: string;
    /** Convert spaces to tabs */
    space_to_tab: boolean;
    /** Convert line endings to POSIX format */
    to_posix_lines: boolean;
    /** Whether to defer the upload (for URL imports) */
    deferred: boolean;
    /** Optional hash values for verification */
    hashes?: FetchDatasetHash[];
}

/** Upload item from a local file */
export interface LocalFileUploadItem extends UploadItemCommon {
    src: "files";
    /** File handle for the local file (File, FileStream, or NamedBlob) */
    fileData: UploadableFile;
}

/** Upload item from pasted text content */
export interface PastedContentUploadItem extends UploadItemCommon {
    src: "pasted";
    /** The pasted text content */
    paste_content: string;
}

/** Upload item from a URL */
export interface UrlUploadItem extends UploadItemCommon {
    src: "url";
    /** The URL to import from */
    url: string;
}

/** Discriminated union of all upload item types */
export type UploadItem = LocalFileUploadItem | PastedContentUploadItem | UrlUploadItem;

/**
 * API-ready upload payload that can be sent directly to /api/tools/fetch.
 * Extends the standard FetchDataPayload with local files for TUS upload.
 */
export interface UploadPayload {
    /** Target history ID */
    history_id: string;
    /** Upload targets with elements */
    targets: HdasUploadTarget[];
    /** Whether to auto-decompress uploads */
    auto_decompress: boolean;
    /** Local files to upload via TUS (not part of API, processed by submitDatasetUpload) */
    files: UploadableFile[];
}

/** Options for building upload payloads */
export interface BuildPayloadOptions {
    /** Whether this is a composite upload (multiple files as one dataset) */
    composite?: boolean;
}

/**
 * Checks if an object is an uploadable file (File, NamedBlob, or FileStream).
 */
export function isUploadableFile(obj: unknown): obj is UploadableFile {
    if (!obj || typeof obj !== "object") {
        return false;
    }
    // Check for FileStream (has isStream: true property)
    if ("isStream" in obj && (obj as FileStream).isStream === true) {
        return true;
    }
    // Check for File or Blob with size
    if ("size" in obj && typeof (obj as File | Blob).size === "number") {
        return obj instanceof File || obj instanceof Blob;
    }
    return false;
}

/**
 * Checks if a filename matches the Galaxy file naming pattern.
 * Pattern: "Galaxy{number}-[{name}]{extension}" (e.g., "Galaxy5-[MyFile].bed")
 */
export function isGalaxyFileName(filename: string | null | undefined): boolean {
    if (!filename) {
        return false;
    }
    return GALAXY_FILE_PATTERN.test(filename);
}

/**
 * Strips the Galaxy prefix from a filename, returning just the original name.
 * "Galaxy5-[MyFile].bed" → "MyFile"
 */
export function stripGalaxyFilePrefix(filename: string): string {
    return filename.replace(GALAXY_FILE_PATTERN, "$1");
}

/**
 * Normalizes a filename for upload.
 * - Returns null for default file names (server will set the name)
 * - Strips Galaxy prefixes from re-uploaded files
 */
function normalizeFileName(filename: string): string | null {
    if (filename === DEFAULT_FILE_NAME) {
        return null;
    }
    if (isGalaxyFileName(filename)) {
        return stripGalaxyFilePrefix(filename);
    }
    return filename;
}

/**
 * Builds an API-conforming data element from an upload item.
 * Returns the element ready for the API payload.
 */
function buildDataElement(item: UploadItem): ApiDataElement {
    const base = {
        dbkey: item.dbkey,
        ext: item.ext,
        name: normalizeFileName(item.name),
        space_to_tab: item.space_to_tab,
        to_posix_lines: item.to_posix_lines,
        auto_decompress: false,
        deferred: item.deferred,
    };

    switch (item.src) {
        case "files": {
            const element: FileDataElement = {
                ...base,
                src: "files",
            };
            if (item.hashes && item.hashes.length > 0) {
                element.hashes = item.hashes;
            }
            return element;
        }

        case "pasted": {
            const element: PastedDataElement = {
                ...base,
                src: "pasted",
                paste_content: item.paste_content,
            };
            return element;
        }

        case "url": {
            const element: UrlDataElement = {
                ...base,
                src: "url",
                url: item.url,
            };
            if (item.hashes && item.hashes.length > 0) {
                element.hashes = item.hashes;
            }
            return element;
        }
    }
}

/**
 * Validates that an upload item has content.
 * @throws Error if the item has no content
 */
function validateItemContent(item: UploadItem): void {
    switch (item.src) {
        case "files":
            if (!item.fileData) {
                throw new Error(`No file data for upload item: ${item.name}`);
            }
            if (item.fileData.size === 0) {
                throw new Error(`File data is empty for upload item: ${item.name}`);
            }
            break;
        case "pasted":
            if (!item.paste_content || item.paste_content.trim().length === 0) {
                throw new Error(`No content for pasted upload item: ${item.name}`);
            }
            break;
        case "url":
            if (!item.url || item.url.trim().length === 0) {
                throw new Error(`No URL for upload item: ${item.name}`);
            }
            if (!isUrl(item.url)) {
                throw new Error(`Invalid URL: ${item.url}`);
            }
            break;
    }
}

/**
 * Builds an API-ready upload payload from a list of upload items.
 *
 * @param items - The upload items to include in the payload
 * @param options - Optional configuration for payload building
 * @returns API-ready payload for sendPayload or submitDatasetUpload
 * @throws Error if no valid items are provided or validation fails
 */
export function buildUploadPayload(items: UploadItem[], options: BuildPayloadOptions = {}): UploadPayload {
    const { composite = false } = options;

    if (items.length === 0) {
        throw new Error("No upload items provided.");
    }

    // All items must have the same target history
    const historyId = items[0]!.historyId;
    if (items.some((item) => item.historyId !== historyId)) {
        throw new Error("All upload items must target the same history.");
    }

    // Validate and build elements
    const files: UploadableFile[] = [];
    const elements: ApiDataElement[] = [];

    for (const item of items) {
        validateItemContent(item);
        elements.push(buildDataElement(item));

        // Collect files for TUS upload
        if (item.src === "files") {
            files.push(item.fileData);
        }
    }

    // Handle composite uploads (multiple files as one dataset)
    if (composite && elements.length > 0) {
        const firstItem = items[0]!;
        const compositeElement: CompositeDataElement = {
            src: "composite",
            dbkey: firstItem.dbkey,
            ext: firstItem.ext,
            auto_decompress: false,
            deferred: false,
            space_to_tab: firstItem.space_to_tab,
            to_posix_lines: firstItem.to_posix_lines,
            composite: {
                elements,
            },
        };
        return {
            history_id: historyId,
            targets: [
                {
                    auto_decompress: false,
                    destination: { type: "hdas" },
                    elements: [compositeElement],
                },
            ],
            auto_decompress: true,
            files,
        };
    }

    return {
        history_id: historyId,
        targets: [
            {
                auto_decompress: false,
                destination: { type: "hdas" },
                elements,
            },
        ],
        auto_decompress: true,
        files,
    };
}

/**
 * Default values for upload item properties.
 */
export const uploadItemDefaults = {
    dbkey: "?",
    ext: "auto",
    space_to_tab: false,
    to_posix_lines: true,
    deferred: false,
} as const;

/**
 * Creates a local file upload item.
 */
export function createFileUploadItem(
    fileData: UploadableFile,
    historyId: string,
    options: Partial<Omit<LocalFileUploadItem, "src" | "fileData" | "historyId">> = {},
): LocalFileUploadItem {
    return {
        src: "files",
        fileData,
        historyId,
        name: options.name ?? ("name" in fileData ? fileData.name : DEFAULT_FILE_NAME),
        size: options.size ?? fileData.size,
        dbkey: options.dbkey ?? uploadItemDefaults.dbkey,
        ext: options.ext ?? uploadItemDefaults.ext,
        space_to_tab: options.space_to_tab ?? uploadItemDefaults.space_to_tab,
        to_posix_lines: options.to_posix_lines ?? uploadItemDefaults.to_posix_lines,
        deferred: options.deferred ?? uploadItemDefaults.deferred,
        hashes: options.hashes,
    };
}

/**
 * Creates a pasted content upload item.
 */
export function createPastedUploadItem(
    paste_content: string,
    historyId: string,
    options: Partial<Omit<PastedContentUploadItem, "src" | "paste_content" | "historyId">> = {},
): PastedContentUploadItem {
    return {
        src: "pasted",
        paste_content,
        historyId,
        name: options.name ?? DEFAULT_FILE_NAME,
        size: options.size ?? paste_content.length,
        dbkey: options.dbkey ?? uploadItemDefaults.dbkey,
        ext: options.ext ?? uploadItemDefaults.ext,
        space_to_tab: options.space_to_tab ?? uploadItemDefaults.space_to_tab,
        to_posix_lines: options.to_posix_lines ?? uploadItemDefaults.to_posix_lines,
        deferred: options.deferred ?? uploadItemDefaults.deferred,
        hashes: options.hashes,
    };
}

/**
 * Creates a URL upload item.
 */
export function createUrlUploadItem(
    url: string,
    historyId: string,
    options: Partial<Omit<UrlUploadItem, "src" | "url" | "historyId">> = {},
): UrlUploadItem {
    // Extract filename from URL if not provided
    const defaultName = url.split("/").pop()?.split("?")[0] || DEFAULT_FILE_NAME;

    return {
        src: "url",
        url,
        historyId,
        name: options.name ?? defaultName,
        size: options.size ?? 0,
        dbkey: options.dbkey ?? uploadItemDefaults.dbkey,
        ext: options.ext ?? uploadItemDefaults.ext,
        space_to_tab: options.space_to_tab ?? uploadItemDefaults.space_to_tab,
        to_posix_lines: options.to_posix_lines ?? uploadItemDefaults.to_posix_lines,
        deferred: options.deferred ?? uploadItemDefaults.deferred,
        hashes: options.hashes,
    };
}

/**
 * Parses text content that may contain URLs (one per line) or plain text.
 * Returns appropriate upload items based on the content.
 *
 * @param content - Text content that may be URLs or pasted data
 * @param historyId - Target history ID
 * @param options - Common options for all created items
 * @returns Array of upload items (URLs become UrlUploadItem, text becomes PastedContentUploadItem)
 */
export function parseContentToUploadItems(
    content: string,
    historyId: string,
    options: Partial<Omit<UploadItemCommon, "historyId" | "name" | "size">> = {},
): UploadItem[] {
    const trimmedContent = content.trim();
    if (!trimmedContent || trimmedContent.length === 0) {
        throw new Error("Content not available.");
    }

    const lines = trimmedContent.split("\n").map((line) => line.trim());
    const firstLine = lines[0] || "";

    // If first line is a URL, treat all lines as URLs
    if (isUrl(firstLine)) {
        return lines.filter(Boolean).map((urlLine) => {
            if (!isUrl(urlLine)) {
                throw new Error(`Invalid URL: ${urlLine}`);
            }
            return createUrlUploadItem(urlLine, historyId, options);
        });
    }

    // Otherwise treat as pasted content
    return [createPastedUploadItem(content, historyId, options)];
}

/**
 * Legacy upload item format (UI model format with camelCase naming).
 * These types and functions maintain backward compatibility with existing consumers.
 * New code should use the modern types and buildUploadPayload directly.
 * @deprecated Use UploadItem types instead. This is an alias for UploadRowModel.
 */
export type LegacyUploadItem = UploadRowModel;

/**
 * Converts a legacy upload item to the new UploadItem format.
 * @deprecated Use UploadItem types directly
 */
export function fromLegacyUploadItem(legacy: LegacyUploadItem, historyId: string): UploadItem | UploadItem[] | null {
    const baseOptions = {
        dbkey: legacy.dbKey || uploadItemDefaults.dbkey,
        ext: legacy.extension || uploadItemDefaults.ext,
        space_to_tab: legacy.spaceToTab ?? uploadItemDefaults.space_to_tab,
        to_posix_lines: legacy.toPosixLines ?? uploadItemDefaults.to_posix_lines,
        deferred: legacy.deferred ?? uploadItemDefaults.deferred,
    };

    switch (legacy.fileMode) {
        case "local":
            if (!legacy.fileData) {
                return null;
            }
            return createFileUploadItem(legacy.fileData, historyId, {
                name: legacy.fileName || DEFAULT_FILE_NAME,
                size: legacy.fileSize || 0,
                ...baseOptions,
            });

        case "new":
            if (!legacy.fileContent || legacy.fileContent.trim().length === 0) {
                throw new Error("Content not available.");
            }
            // Use parseContentToUploadItems to handle URL detection in pasted content
            return parseContentToUploadItems(legacy.fileContent, historyId, baseOptions);

        case "url": {
            const url = legacy.fileUri || legacy.filePath || legacy.fileContent;
            if (!url) {
                return null;
            }
            return createUrlUploadItem(url, historyId, {
                name: legacy.fileName || DEFAULT_FILE_NAME,
                size: legacy.fileSize || 0,
                ...baseOptions,
            });
        }

        case "ftp":
            if (!legacy.filePath) {
                return null;
            }
            return createUrlUploadItem(legacy.filePath, historyId, {
                name: legacy.fileName || DEFAULT_FILE_NAME,
                size: legacy.fileSize || 0,
                ...baseOptions,
            });

        default:
            return null;
    }
}

/**
 * Converts an array of legacy upload items to the new UploadItem format.
 * @deprecated Use UploadItem types directly
 */
export function fromLegacyUploadItems(legacyItems: LegacyUploadItem[], historyId: string): UploadItem[] {
    return legacyItems
        .flatMap((item) => fromLegacyUploadItem(item, historyId))
        .filter((item): item is UploadItem => item !== null);
}

/**
 * Builds an upload payload from legacy upload items.
 * This is a compatibility shim for existing consumers.
 * @deprecated Use buildUploadPayload with UploadItem types
 */
export function buildLegacyPayload(
    legacyItems: LegacyUploadItem[],
    historyId: string,
    composite = false,
): UploadPayload {
    if (legacyItems.length === 0) {
        throw new Error("No upload items provided.");
    }

    const items = fromLegacyUploadItems(legacyItems, historyId);

    if (items.length === 0) {
        throw new Error("No valid upload items after conversion.");
    }

    return buildUploadPayload(items, { composite });
}
