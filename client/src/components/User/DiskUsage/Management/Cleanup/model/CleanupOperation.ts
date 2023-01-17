import type { CleanableSummary } from "./CleanableSummary";
import type { CleanupResult } from "./CleanupResult";

export interface PaginationOptions {
    limit?: number;
    offset?: number;
    sortBy?: string;
    sortDesc?: boolean;
}

export interface CleanableItem {
    id: string;
    name: string;
    size: number;
}

/**
 * Represents an operation that can potentially `clean` the user storage.
 * The concept of `cleaning` here refers to any action that can free up
 * some space in the user storage.
 */
export interface CleanupOperation {
    /**
     * The ID of this cleanup operation.
     */
    id: string;

    /**
     * The name of this cleanup operation.
     */
    name: string;

    /**
     * The description of this cleanup operation.
     */
    description: string;

    /**
     * Fetches summary information about the total amount of
     * space that can be cleaned/recovered using this operation.
     */
    fetchSummary: () => Promise<CleanableSummary>;

    /**
     * Fetches an array of items that can be potentially `cleaned` by this operation.
     * @param options The filter options for sorting and pagination of the items.
     * @returns An array of items that can be potentially `cleaned` and match the filtering params.
     */
    fetchItems: (options: PaginationOptions) => Promise<CleanableItem[]>;

    /**
     * Processes the given items to free up some user storage space and provides a result
     * indicating how much was space was recovered or what errors may have ocurred.
     * @param items An array of items to be `cleaned`
     * @returns The result of the cleanup operation.
     */
    cleanupItems: (items: CleanableItem[]) => Promise<CleanupResult>;
}
