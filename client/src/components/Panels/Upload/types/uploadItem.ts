/**
 * Shared type definitions for upload method item types.
 * These types represent the internal state of items in each upload method component
 * before they are converted to upload queue items.
 */

import type { FetchDatasetHash } from "@/api/tools";

/**
 * Base properties shared by all upload method items
 */
export interface BaseUploadItem {
    name: string;
    extension: string;
    dbkey: string;
    spaceToTab: boolean;
    toPosixLines: boolean;
}

/**
 * Item properties for items that need unique identification
 */
export interface IdentifiableUploadItem {
    id: number;
}

/**
 * Item properties for deferred uploads (URLs)
 */
export interface DeferrableUploadItem {
    deferred: boolean;
}

/**
 * Item properties for expandable UI details
 */
export interface ExpandableUploadItem {
    _showDetails?: boolean;
}

/**
 * Local file upload item (used in LocalFileUpload.vue)
 */
export interface LocalFileItem extends BaseUploadItem {
    file: File;
    size: number;
}

/**
 * Pasted content upload item (used in PasteContentUpload.vue)
 */
export interface PasteContentItem extends BaseUploadItem, IdentifiableUploadItem, ExpandableUploadItem {
    content: string;
}

/**
 * URL upload item (used in PasteLinksUpload.vue)
 */
export interface PasteUrlItem extends BaseUploadItem, IdentifiableUploadItem, DeferrableUploadItem {
    url: string;
}

/**
 * Remote file upload item (used in RemoteFilesUpload.vue)
 */
export interface RemoteFileItem extends PasteUrlItem {
    size: number;
    hashes?: FetchDatasetHash[];
}

/**
 * Source mode for a single slot in a composite upload
 */
export type CompositeSlotMode = "local" | "url" | "paste";

/**
 * Represents a single component file slot in a composite upload.
 * Each composite datatype defines a fixed set of named slots (e.g. `.bim`, `.bed`, `.fam` for plink).
 */
export interface CompositeSlot {
    /** Machine name of the slot (e.g. "bim", "affymetrix_cel") */
    slotName: string;
    /** Human-readable description shown to the user */
    description: string;
    /** Whether this slot must be filled before upload */
    optional: boolean;
    /** Currently selected source mode */
    mode: CompositeSlotMode;
    /** Local File object (only present when mode === "local") */
    file?: File;
    /** File size in bytes (derived from file or URL head) */
    fileSize: number;
    /** Remote URL (used when mode === "url") */
    url: string;
    /** Pasted text content (used when mode === "paste") */
    content: string;
}

/**
 * Composite dataset upload item (used in CompositeFileUpload.vue).
 * Represents all component slots that together form one composite HDA.
 */
export interface CompositeFileItem {
    /** Display name for the resulting dataset in history */
    name: string;
    /** Galaxy datatype extension (e.g. "plink", "affybatch") */
    extension: string;
    /** Genome build / database key */
    dbkey: string;
    /** Ordered list of component file slots */
    slots: CompositeSlot[];
}

/**
 * Library dataset upload item (used in DataLibraryUpload.vue)
 * Note: Library datasets are already on the server, so no upload options are needed
 */
export interface LibraryDatasetItem extends IdentifiableUploadItem {
    libraryId: string;
    folderId: string;
    lddaId: string;
    url: string;
    name: string;
    extension: string; // Read-only, from library dataset
    size: number; // raw_size from API
    created?: string;
    updated?: string;
    dateUploaded?: string;
    isUnrestricted?: boolean;
    isPrivate?: boolean;
    tags?: string[];
}
