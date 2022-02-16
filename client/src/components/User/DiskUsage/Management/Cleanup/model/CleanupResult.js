import { bytesToString } from "utils/utils";

/**
 * Contains information about the result of the cleaning operation.
 */
export class CleanupResult {
    constructor(props = {}) {
        this.totalItemCount = props.totalItemCount || 0;
        this.totalFreeBytes = props.totalFreeBytes || 0;
        this.errors = props.errors || [];
        this.errorMessage = props.errorMessage || null;
    }

    /**
     * Whether the cleanup operation yielded some errors.
     * It doesn't mean the operation completely failed.
     * @returns {boolean}
     */
    get hasSomeErrors() {
        return this.errors.length > 0;
    }

    /**
     * Whether the cleanup operation completely failed.
     * This means not even partial cleaning was made.
     * @returns {boolean}
     */
    get hasFailed() {
        return this.errorMessage !== null;
    }

    /**
     * Whether the cleanup operation was executed without errors.
     * @returns {boolean}
     */
    get success() {
        return !this.hasSomeErrors && !this.errorMessage;
    }

    /**
     * The number of items successfully cleaned.
     * @returns {number}
     */
    get totalCleaned() {
        return this.totalItemCount - this.errors.length;
    }

    /**
     * Whether the cleanup operation managed to
     * free some items but not all of them.
     * @returns {boolean}
     */
    get isPartialSuccess() {
        return this.errors.length > 0 && this.totalCleaned > 0;
    }

    /**
     * The total amount of disk space freed by the cleanup operation.
     * @returns {String}
     */
    get niceTotalFreeBytes() {
        return bytesToString(this.totalFreeBytes, true);
    }
}
