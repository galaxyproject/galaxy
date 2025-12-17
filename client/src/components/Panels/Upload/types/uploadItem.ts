/**
 * Shared type definitions for upload method item types.
 * These types represent the internal state of items in each upload method component
 * before they are converted to upload queue items.
 */

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
