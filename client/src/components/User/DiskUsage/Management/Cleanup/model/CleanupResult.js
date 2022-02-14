/**
 * Contains information about the result of the cleaning operation.
 */
export class CleanupResult {
    constructor() {
        this.totalItemCount = 0;
        this.totalFreeBytes = 0;
        this.errors = [];
        this.errorMessage = null;
    }

    /**
     * Whether the cleanup operation yielded some errors.
     * It doesn't mean the operation completely failed.
     * @returns {boolean}
     */
    get hasSomeErrors() {
        return this.errors.length > 0 || this.errorMessage !== null;
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
     * Whether the cleanup operation managed to
     * free some items but not all of them.
     * @returns {boolean}
     */
    get isPartialSuccess() {
        return this.totalItemCount - this.errors.length > 0;
    }
}
