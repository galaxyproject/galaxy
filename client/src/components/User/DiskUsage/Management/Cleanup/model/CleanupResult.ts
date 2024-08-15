import { type components } from "@/api/schema";
import { bytesToString } from "@/utils/utils";

import { type CleanableItem } from "./CleanupOperation";

export type StorageItemsCleanupResult = components["schemas"]["StorageItemsCleanupResult"];

/**
 * Associates the name of an item with the error message when failed.
 * Simplifies displaying information to the final user.
 */
export interface ItemError {
    /** Name of the item. */
    name: string;
    /** The reason why it couldn't be cleaned. */
    reason: string;
}

/**
 * Provides additional information about the result of the cleaning operation.
 */
export class CleanupResult {
    private _data: StorageItemsCleanupResult;
    private _item_id_map: Map<string, CleanableItem>;
    private _errorMessage?: string;

    /**
     * Creates a new CleanupResult.
     * @param data The server response data for a cleanup operation.
     * @param items The list of requested items to be cleaned.
     * @param errorMessage A possible error message if the request completely failed.
     */
    constructor(data?: StorageItemsCleanupResult, items?: CleanableItem[], errorMessage?: string) {
        this._data = data ?? { total_item_count: 0, success_item_count: 0, total_free_bytes: 0, errors: [] };
        items = items ?? [];
        this._item_id_map = new Map<string, CleanableItem>();
        items.forEach((item) => {
            this._item_id_map.set(item.id, item);
        });
        this._errorMessage = errorMessage;
    }

    /**
     * The total number of items requested to be cleaned.
     */
    get totalItemCount(): number {
        return this._data.total_item_count;
    }

    /**
     * The total amount of space in bytes recovered after trying to cleanup all the requested items.
     */
    get totalFreeBytes(): number {
        return this._data.total_free_bytes;
    }

    /**
     * List of error messages associated with a particular item ID.
     * When an item cannot be cleaned it will be registered in this list.
     */
    get errors(): ItemError[] {
        return this._data.errors.map((e) => {
            return { name: this._item_id_map.get(e.item_id)?.name ?? "Unknown", reason: e.error };
        });
    }

    /**
     * A general error message, usually indicating that the whole cleanup operation failed with
     * no partial success.
     */
    get errorMessage(): string | undefined {
        return this._errorMessage;
    }

    /**
     * Whether the cleanup operation could not success for every requested item.
     * It doesn't mean the operation completely failed, some items could have been successfully cleaned.
     */
    get hasSomeErrors(): boolean {
        return this._data.errors.length > 0;
    }

    /**
     * Whether the cleanup operation completely failed.
     * This means not even partial cleaning was made.
     */
    get hasFailed(): boolean {
        return Boolean(this._errorMessage);
    }

    /**
     * Whether the cleanup operation was executed without errors.
     */
    get success(): boolean {
        return !this.hasSomeErrors && !this.hasFailed;
    }

    /**
     * The number of items successfully cleaned.
     */
    get totalCleaned(): number {
        return this._data.success_item_count;
    }

    /**
     * Whether the cleanup operation managed to free some items but not all of them.
     */
    get isPartialSuccess(): boolean {
        return this.hasSomeErrors && this._data.success_item_count > 0;
    }

    /**
     * Whether the cleanup operation managed to free some space or remove some items.
     * It can happen that only "copy" items were removed effectively recovering 0 bytes.
     */
    get hasUpdatedResults(): boolean {
        return this.totalFreeBytes > 0 || this.totalCleaned > 0;
    }

    /**
     * The total amount of disk space freed by the cleanup operation.
     */
    get niceTotalFreeBytes(): string {
        return bytesToString(this._data.total_free_bytes, true, undefined);
    }
}
