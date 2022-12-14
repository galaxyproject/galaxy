import { bytesToString } from "@/utils/utils";

export interface ItemError {
    name: string;
    reason: string;
}

export interface CleanupResultResponse {
    totalItemCount: number;
    totalFreeBytes: number;
    errors: ItemError[];
    errorMessage?: string;
}

/**
 * Contains information about the result of the cleaning operation.
 */
export class CleanupResult {
    private _data: CleanupResultResponse;

    constructor(data: CleanupResultResponse = { totalFreeBytes: 0, totalItemCount: 0, errors: [] }) {
        this._data = data;
    }

    get totalItemCount(): number {
        return this._data.totalItemCount;
    }

    get totalFreeBytes(): number {
        return this._data.totalFreeBytes;
    }

    get errors(): ItemError[] {
        return this._data.errors;
    }

    get errorMessage(): string | undefined {
        return this._data.errorMessage;
    }

    /**
     * Whether the cleanup operation yielded some errors.
     * It doesn't mean the operation completely failed.
     * @returns {boolean}
     */
    get hasSomeErrors(): boolean {
        return this._data.errors.length > 0;
    }

    /**
     * Whether the cleanup operation completely failed.
     * This means not even partial cleaning was made.
     * @returns {boolean}
     */
    get hasFailed(): boolean {
        return Boolean(this._data.errorMessage);
    }

    /**
     * Whether the cleanup operation was executed without errors.
     * @returns {boolean}
     */
    get success(): boolean {
        return !this.hasSomeErrors && !this._data.errorMessage;
    }

    /**
     * The number of items successfully cleaned.
     * @returns {number}
     */
    get totalCleaned(): number {
        return this._data.totalItemCount - this._data.errors.length;
    }

    /**
     * Whether the cleanup operation managed to
     * free some items but not all of them.
     * @returns {boolean}
     */
    get isPartialSuccess(): boolean {
        return this._data.errors.length > 0 && this.totalCleaned > 0;
    }

    /**
     * The total amount of disk space freed by the cleanup operation.
     * @returns {String}
     */
    get niceTotalFreeBytes(): string {
        return bytesToString(this._data.totalFreeBytes, true, undefined);
    }
}
