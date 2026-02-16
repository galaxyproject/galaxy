/**
 * Unified upload utilities for Galaxy dataset uploads.
 *
 * This module provides a complete API for building and submitting upload payloads
 * to the /api/tools/fetch endpoint. It handles:
 * - Local file uploads via TUS chunked protocol
 * - Pasted content uploads
 * - URL imports (deferred or immediate)
 * - Composite uploads (multiple files as one dataset)
 *
 * All types use API naming conventions directly (dbkey, ext, space_to_tab, etc.)
 * to avoid unnecessary transformation layers.
 *
 * @example
 * ```typescript
 * // Simple file upload
 * await uploadDatasets([
 *   createFileUploadItem(file, "history123", { ext: "bed" }),
 * ], {
 *   success: (response) => console.log("Upload complete", response),
 *   error: (err) => console.error("Upload failed", err),
 * });
 *
 * // URL import
 * await uploadDatasets([
 *   createUrlUploadItem("https://example.com/data.txt", "history123"),
 * ]);
 *
 * // Pasted content
 * await uploadDatasets([
 *   createPastedUploadItem("sequence data here", "history123", { ext: "fasta" }),
 * ]);
 * ```
 */
import {
    type ApiDataElement,
    type CompositeDataElement,
    type FetchDataPayload,
    type FetchDatasetHash,
    fetchDatasets,
    type FetchDatasetsCallbacks,
    type FileDataElement,
    type HdasUploadTarget,
    type HdcaUploadTarget,
    type NestedElement,
    type PastedDataElement,
    type UrlDataElement,
} from "@/api/tools";
import type { UploadRowModel } from "@/components/Upload/model";
import type { SupportedCollectionType } from "@/composables/upload/collectionTypes";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";
import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString } from "@/utils/simple-error";
import { isUrl } from "@/utils/url";

import { COMMON_FILTERS, DEFAULT_FILTER, guessInitialFilterType, guessNameForPair } from "@/components/Collections/pairing";

import { createTusUpload, type FileStream, type NamedBlob, type UploadableFile } from "./tusUpload";

// ============================================================================
// Re-exports for convenience
// ============================================================================

/** Re-export TUS upload types */
export type { FileStream, NamedBlob, UploadableFile } from "./tusUpload";

/** Re-export API types commonly used with uploads */
export type {
    ApiDataElement,
    CompositeDataElement,
    FetchDataPayload,
    FetchDatasetHash,
    FetchDatasetsCallbacks,
    FileDataElement,
    HdasUploadTarget,
    HdcaUploadTarget,
    NestedElement,
    PastedDataElement,
    UrlDataElement,
} from "@/api/tools";

/** Re-export fetchDatasets for direct API calls (e.g., URL uploads without TUS) */
export { fetchDatasets } from "@/api/tools";

// ============================================================================
// Constants
// ============================================================================

/** Default file name used when no name is provided */
export const DEFAULT_FILE_NAME = "New File";

/** Default chunk size for TUS uploads (10MB) */
export const DEFAULT_CHUNK_SIZE = 10485760;

/** Regex pattern for Galaxy-formatted file names (e.g., "Galaxy5-[FileName].bed") */
const GALAXY_FILE_PATTERN = /Galaxy\d+-\[(.*?)\](\..+)/;

// ============================================================================
// Upload Item Types
// ============================================================================

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
export type ApiUploadItem = LocalFileUploadItem | PastedContentUploadItem | UrlUploadItem;

// ============================================================================
// Payload Types
// ============================================================================

/**
 * API-ready upload payload that can be sent directly to /api/tools/fetch.
 * Extends the standard FetchDataPayload with local files for TUS upload.
 */
export interface UploadPayload {
    /** Target history ID */
    history_id: string;
    /** Upload targets with elements (HDA for individual datasets, HDCA for collections) */
    targets: (HdasUploadTarget | HdcaUploadTarget)[];
    /** Whether to auto-decompress uploads */
    auto_decompress: boolean;
    /** Local files to upload via TUS (not part of API, processed by submitUpload) */
    files: UploadableFile[];
}

/**
 * Upload payload with optional error message for validation failures.
 */
export interface UploadDataPayload extends UploadPayload {
    /** Optional error message that will cause immediate failure */
    error_message?: string;
}

/** Options for building upload payloads */
export interface BuildPayloadOptions {
    /** Whether this is a composite upload (multiple files as one dataset) */
    composite?: boolean;
}

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * Configuration for upload submission.
 */
export interface UploadSubmitConfig extends FetchDatasetsCallbacks {
    /** The upload payload data */
    data: UploadDataPayload;
    /** Whether this is a composite upload */
    isComposite?: boolean;
    /** Chunk size for TUS uploads in bytes (default: 10MB) */
    chunkSize?: number;
}

/**
 * Configuration for the uploadDatasets function.
 */
export interface UploadDatasetsConfig extends FetchDatasetsCallbacks, BuildPayloadOptions {
    /** Chunk size for TUS uploads in bytes (default: 10MB) */
    chunkSize?: number;
}

// ============================================================================
// Default Values
// ============================================================================

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

// ============================================================================
// Type Guards and Utilities
// ============================================================================

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
 * Cleans a filename that may have URL encoding or query parameters.
 * - Extracts the base filename (after last /)
 * - Removes query parameters (everything after ?)
 * - Decodes URL-encoded characters (%20 → space, etc.)
 *
 * @example
 * cleanUrlFilename("https://example.com/path/to%20file.txt?version=1") → "to file.txt"
 * cleanUrlFilename("normal.txt") → "normal.txt"
 */
export function cleanUrlFilename(filename: string): string | null {
    // Remove query parameters
    const defaultName = filename.split("/").pop()?.split("?")[0];
    if (!defaultName) {
        return null;
    }
    // Decode URL-encoded characters
    try {
        return decodeURIComponent(defaultName);
    } catch {
        // If decoding fails (malformed encoding), return as-is without query params
        return defaultName;
    }
}

/**
 * Normalizes a filename for upload.
 * - Returns null for default file names (server will set the name)
 * - Strips Galaxy prefixes from re-uploaded files
 * - Cleans URL-encoded characters and query parameters
 */
function normalizeFileName(filename: string): string | null {
    if (filename === DEFAULT_FILE_NAME) {
        return null;
    }
    if (isGalaxyFileName(filename)) {
        return stripGalaxyFilePrefix(filename);
    }
    return cleanUrlFilename(filename);
}

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Creates a local file upload item.
 *
 * @param fileData - The file to upload (File, NamedBlob, or FileStream)
 * @param historyId - Target history ID
 * @param options - Optional properties to override defaults
 * @returns A LocalFileUploadItem ready for upload
 *
 * @example
 * ```typescript
 * const item = createFileUploadItem(file, "history123", {
 *   ext: "bed",
 *   dbkey: "hg38",
 * });
 * ```
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
 *
 * @param paste_content - The text content to upload
 * @param historyId - Target history ID
 * @param options - Optional properties to override defaults
 * @returns A PastedContentUploadItem ready for upload
 *
 * @example
 * ```typescript
 * const item = createPastedUploadItem(">seq1\nACGT", "history123", {
 *   ext: "fasta",
 *   name: "my_sequences.fasta",
 * });
 * ```
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
 *
 * @param url - The URL to import from
 * @param historyId - Target history ID
 * @param options - Optional properties to override defaults
 * @returns A UrlUploadItem ready for upload
 *
 * @example
 * ```typescript
 * const item = createUrlUploadItem(
 *   "https://example.com/data.bed",
 *   "history123",
 *   { deferred: true }
 * );
 * ```
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
 * Converts a UI upload item to an API-ready upload item.
 *
 * This bridges the gap between:
 * - NewUploadItem: UI-friendly format with camelCase (persisted in localStorage)
 * - ApiUploadItem: API-ready format with snake_case (sent to server)
 *
 * @param item - The UI upload item to convert
 * @returns API-ready upload item
 * @throws Error if item has invalid uploadMode or missing required data
 */
export function toApiUploadItem(item: NewUploadItem): ApiUploadItem {
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
        case "remote-files":
            return createUrlUploadItem(item.url, item.targetHistoryId, baseOptions);

        default:
            throw new Error(`Unsupported upload mode: ${item.uploadMode}`);
    }
}

/**
 * Parses text content that may contain URLs (one per line) or plain text.
 * Returns appropriate upload items based on the content.
 *
 * @param content - Text content that may be URLs or pasted data
 * @param historyId - Target history ID
 * @param options - Common options for all created items
 * @returns Array of upload items (URLs become UrlUploadItem, text becomes PastedContentUploadItem)
 * @throws Error if content is empty
 *
 * @example
 * ```typescript
 * // Parse URLs
 * const items = parseContentToUploadItems(
 *   "https://example.com/file1.bed\nhttps://example.com/file2.bed",
 *   "history123"
 * );
 * // Returns: [UrlUploadItem, UrlUploadItem]
 *
 * // Parse text
 * const items = parseContentToUploadItems(">seq1\nACGT", "history123");
 * // Returns: [PastedContentUploadItem]
 * ```
 */
export function parseContentToUploadItems(
    content: string,
    historyId: string,
    options: Partial<Omit<UploadItemCommon, "historyId" | "name" | "size">> = {},
): ApiUploadItem[] {
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

// ============================================================================
// Payload Building (Internal)
// ============================================================================

/**
 * Builds an API-conforming data element from an upload item.
 * Returns the element ready for the API payload.
 */
function buildDataElement(item: ApiUploadItem): ApiDataElement {
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
function validateItemContent(item: ApiUploadItem): void {
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
 * @returns API-ready payload for submitUpload
 * @throws Error if no valid items are provided or validation fails
 */
export function buildUploadPayload(items: ApiUploadItem[], options: BuildPayloadOptions = {}): UploadPayload {
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

// ============================================================================
// Collection Upload Payload Building
// ============================================================================

/** Options for building collection upload payloads */
export interface CollectionUploadOptions {
    /** Collection display name */
    collectionName: string;
    /** Collection type: 'list' or 'list:paired' */
    collectionType: SupportedCollectionType;
}

/**
 * Builds nested paired elements from a flat list of data elements.
 * Groups consecutive pairs with "forward"/"reverse" names inside NestedElement wrappers.
 * Uses the shared pairing abstractions from @/components/Collections/pairing for
 * pair name extraction (synchronized with the backend via auto_pairing_spec.yml).
 *
 * IMPORTANT: The files array order must match depth-first element traversal order.
 * For list:paired, the backend's replace_file_srcs iterates depth-first:
 * pair1-forward, pair1-reverse, pair2-forward, pair2-reverse, etc.
 * This matches the original item order, so no reordering is needed.
 */
function buildPairedElements(items: ApiUploadItem[], dataElements: ApiDataElement[]): NestedElement[] {
    const pairs: NestedElement[] = [];
    const usedNames = new Set<string>();

    // Use the shared filter detection to determine forward/reverse naming convention
    const filterType = guessInitialFilterType(items) ?? DEFAULT_FILTER;
    const [forwardFilter, reverseFilter] = COMMON_FILTERS[filterType];

    for (let i = 0; i < items.length; i += 2) {
        if (i + 1 >= items.length) {
            console.warn(`Skipping unpaired file at index ${i}: ${items[i]?.name}`);
            break;
        }

        const item1 = items[i]!;
        const item2 = items[i + 1]!;

        const basePairName =
            guessNameForPair(item1, item2, forwardFilter, reverseFilter, true) ||
            `pair_${Math.floor(i / 2) + 1}`;
        let pairName = basePairName;
        let counter = 1;
        while (usedNames.has(pairName)) {
            pairName = `${basePairName}_${counter}`;
            counter++;
        }
        usedNames.add(pairName);

        const nestedElement: NestedElement = {
            name: pairName,
            elements: [
                { ...dataElements[i]!, name: "forward" },
                { ...dataElements[i + 1]!, name: "reverse" },
            ],
            auto_decompress: false,
            dbkey: "?",
            ext: "auto",
            space_to_tab: false,
            to_posix_lines: false,
            deferred: false,
        };
        pairs.push(nestedElement);
    }

    return pairs;
}

/**
 * Builds an API-ready upload payload that creates a dataset collection directly.
 * Uses HdcaDataItemsTarget with destination { type: "hdca" } so the collection
 * is created atomically in a single /api/tools/fetch request.
 *
 * @param items - The upload items to include in the collection
 * @param options - Collection configuration (name and type)
 * @returns API-ready payload for submitUpload
 * @throws Error if no valid items are provided or validation fails
 */
export function buildCollectionUploadPayload(items: ApiUploadItem[], options: CollectionUploadOptions): UploadPayload {
    if (items.length === 0) {
        throw new Error("No upload items provided.");
    }

    const historyId = items[0]!.historyId;
    if (items.some((item) => item.historyId !== historyId)) {
        throw new Error("All upload items must target the same history.");
    }

    const files: UploadableFile[] = [];
    const dataElements: ApiDataElement[] = [];

    for (const item of items) {
        validateItemContent(item);
        dataElements.push(buildDataElement(item));
        if (item.src === "files") {
            files.push(item.fileData);
        }
    }

    let elements: HdcaUploadTarget["elements"];

    if (options.collectionType === "list") {
        elements = dataElements;
    } else if (options.collectionType === "list:paired") {
        elements = buildPairedElements(items, dataElements);
    } else {
        throw new Error(`Unsupported collection type: ${options.collectionType}`);
    }

    const target: HdcaUploadTarget = {
        auto_decompress: false,
        destination: { type: "hdca" },
        collection_type: options.collectionType,
        name: options.collectionName,
        elements,
    };

    return {
        history_id: historyId,
        targets: [target],
        auto_decompress: true,
        files,
    };
}

// ============================================================================
// Upload Submission
// ============================================================================

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
    callbacks: FetchDatasetsCallbacks,
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

        await fetchDatasets(apiPayload as FetchDataPayload, callbacks);
    } catch (err) {
        // Ensure error callback is invoked
        if (err instanceof Error) {
            callbacks.error?.(err);
        }
    }
}

/**
 * Submits files for upload to Galaxy.
 * Handles TUS chunked uploads for files and direct payload submission for URLs.
 *
 * @param config - Upload configuration including payload and callbacks
 */
export async function submitUpload(config: UploadSubmitConfig): Promise<void> {
    const {
        data,
        success = () => {},
        error = () => {},
        warning = () => {},
        progress = () => {},
        isComposite = false,
        chunkSize = DEFAULT_CHUNK_SIZE,
    } = config;

    // Initial validation
    if (data.error_message) {
        error(data.error_message);
        return;
    }

    const tusEndpoint = `${getAppRoot()}api/upload/resumable_upload/`;
    const callbacks: FetchDatasetsCallbacks = { success, error, warning, progress };

    // Determine upload path based on data structure
    const hasFiles = data.files && data.files.length > 0;

    if (hasFiles || isComposite) {
        // Upload files via TUS, then submit payload
        await uploadFilesViaTus(data, tusEndpoint, chunkSize, callbacks);
    } else if (data.targets && data.targets.length > 0) {
        const firstTarget = data.targets[0];

        // Check if this is a collection (HDCA) target
        if (firstTarget && "destination" in firstTarget && firstTarget.destination.type === "hdca") {
            // HDCA collection target with no local files (all URLs/pasted) - submit directly
            const apiPayload = toApiPayload(data);
            await fetchDatasets(apiPayload, callbacks);
        } else if (
            firstTarget &&
            "elements" in firstTarget &&
            firstTarget.elements &&
            firstTarget.elements.length > 0
        ) {
            // Handle HDA URL or pasted content
            const firstElement = firstTarget.elements[0];

            if (firstElement && "src" in firstElement) {
                if (firstElement.src === "url") {
                    // Direct URL submission - no TUS upload needed
                    const apiPayload = toApiPayload(data);
                    await fetchDatasets(apiPayload, callbacks);
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
 * Uploads datasets to Galaxy with a simplified API.
 * Combines payload building, TUS file upload, and API submission in one call.
 *
 * This is the primary entry point for upload workflows.
 *
 * @param items - The upload items to process
 * @param config - Upload configuration and callbacks
 *
 * @example
 * ```typescript
 * // Upload a file
 * await uploadDatasets([
 *   createFileUploadItem(file, "history123", { ext: "bed" }),
 * ], {
 *   success: (response) => console.log("Upload complete", response),
 *   error: (err) => console.error("Upload failed", err),
 *   progress: (pct) => console.log(`Progress: ${pct}%`),
 * });
 *
 * // Upload multiple URLs
 * await uploadDatasets([
 *   createUrlUploadItem("https://example.com/data1.txt", "history123"),
 *   createUrlUploadItem("https://example.com/data2.txt", "history123"),
 * ]);
 *
 * // Composite upload (multiple files as one dataset)
 * await uploadDatasets(items, { composite: true });
 * ```
 */
export async function uploadDatasets(items: ApiUploadItem[], config: UploadDatasetsConfig = {}): Promise<void> {
    const { composite = false, chunkSize, success, error, warning, progress } = config;

    try {
        // Build the API-ready payload from upload items
        const payload = buildUploadPayload(items, { composite });

        // Prepare the data for submission
        const data: UploadDataPayload = {
            history_id: payload.history_id,
            targets: payload.targets,
            auto_decompress: payload.auto_decompress,
            files: payload.files,
        };

        // Submit using the unified upload infrastructure
        await submitUpload({
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

/**
 * Uploads datasets as a collection directly via a single /api/tools/fetch request.
 * Uses HdcaDataItemsTarget to create the collection atomically during the fetch.
 *
 * @param items - The upload items to include in the collection
 * @param collectionOptions - Collection name and type
 * @param config - Upload configuration and callbacks
 *
 * @example
 * ```typescript
 * await uploadCollectionDatasets(
 *   [
 *     createUrlUploadItem("https://example.com/1.txt", "history123"),
 *     createUrlUploadItem("https://example.com/2.txt", "history123"),
 *   ],
 *   { collectionName: "My List", collectionType: "list" },
 *   { success: (response) => console.log("Collection created", response) },
 * );
 * ```
 */
export async function uploadCollectionDatasets(
    items: ApiUploadItem[],
    collectionOptions: CollectionUploadOptions,
    config: UploadDatasetsConfig = {},
): Promise<void> {
    const { chunkSize, success, error, warning, progress } = config;

    try {
        const payload = buildCollectionUploadPayload(items, collectionOptions);

        const data: UploadDataPayload = {
            history_id: payload.history_id,
            targets: payload.targets,
            auto_decompress: payload.auto_decompress,
            files: payload.files,
        };

        await submitUpload({
            data,
            chunkSize,
            success,
            error,
            warning,
            progress,
        });
    } catch (err) {
        config.error?.(errorMessageAsString(err));
    }
}

// ============================================================================
// Legacy Compatibility Layer
// ============================================================================

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
export function fromLegacyUploadItem(
    legacy: LegacyUploadItem,
    historyId: string,
): ApiUploadItem | ApiUploadItem[] | null {
    const baseOptions = {
        name: legacy.fileName || DEFAULT_FILE_NAME,
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
                size: legacy.fileSize || 0,
                ...baseOptions,
            });
        }

        case "ftp":
            if (!legacy.filePath) {
                return null;
            }
            return createUrlUploadItem(legacy.filePath, historyId, {
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
export function fromLegacyUploadItems(legacyItems: LegacyUploadItem[], historyId: string): ApiUploadItem[] {
    return legacyItems
        .flatMap((item) => fromLegacyUploadItem(item, historyId))
        .filter((item): item is ApiUploadItem => item !== null);
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

// ============================================================================
// Backward Compatibility Aliases
// ============================================================================

/**
 * @deprecated Use submitUpload instead
 */
export const submitDatasetUpload = submitUpload;

/**
 * @deprecated Use FetchDatasetsCallbacks from @/api/tools instead
 */
export type UploadCallbacks = FetchDatasetsCallbacks;
