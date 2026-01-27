import type { components } from "@/api";
import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export type LibrarySummary = components["schemas"]["LibrarySummary"];
export type LibraryFolderDetails = components["schemas"]["LibraryFolderDetails"];
export type LibraryFolderContentsIndexResult = components["schemas"]["LibraryFolderContentsIndexResult"];
export type FileLibraryFolderItem = components["schemas"]["FileLibraryFolderItem"];
export type FolderLibraryFolderItem = components["schemas"]["FolderLibraryFolderItem"];
export type AnyLibraryFolderItem = FileLibraryFolderItem | FolderLibraryFolderItem;

export type SortBy = "name" | "description" | "type" | "size" | "update_time";

/**
 * Options for fetching folder contents
 */
export interface GetFolderContentsOptions {
    /** Search term to filter items by name/description */
    searchText?: string;
    /** Field to sort by */
    sortBy?: SortBy;
    /** Sort in descending order */
    sortDesc?: boolean;
    /** Maximum number of items to return */
    limit?: number;
    /** Number of items to skip */
    offset?: number;
    /** Whether to include deleted items */
    includeDeleted?: boolean;
}

/**
 * Fetches all libraries accessible to the current user.
 * Libraries without access permissions are filtered out by the backend.
 */
export async function getLibraries(): Promise<LibrarySummary[]> {
    const { data, error } = await GalaxyApi().GET("/api/libraries", {
        params: {},
    });

    if (error) {
        rethrowSimple(error);
    }

    return data || [];
}

/**
 * Fetches details for a specific library.
 */
export async function getLibrary(libraryId: string): Promise<LibrarySummary> {
    const { data, error } = await GalaxyApi().GET("/api/libraries/{id}", {
        params: {
            path: { id: libraryId },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}

/**
 * Fetches the contents of a library folder.
 * Datasets without access permissions are filtered out by the backend.
 * Deleted items are not included by default; set `includeDeleted` to true to include them.
 */
export async function getFolderContents(
    folderId: string,
    options: GetFolderContentsOptions = {},
): Promise<LibraryFolderContentsIndexResult> {
    const { data, error } = await GalaxyApi().GET("/api/folders/{folder_id}/contents", {
        params: {
            path: { folder_id: folderId },
            query: {
                include_deleted: options.includeDeleted || false,
                search_text: options.searchText,
                order_by: options.sortBy,
                sort_desc: options.sortDesc,
                limit: options.limit || 25,
                offset: options.offset || 0,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}

export function isLibraryFolder(item: AnyLibraryFolderItem | Record<string, unknown>): item is FolderLibraryFolderItem {
    return item.type === "folder";
}

export function isLibraryFile(item: AnyLibraryFolderItem | Record<string, unknown>): item is FileLibraryFolderItem {
    return item.type === "file";
}
