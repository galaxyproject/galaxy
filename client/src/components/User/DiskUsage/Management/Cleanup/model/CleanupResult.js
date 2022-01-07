/**
 * Contains information about the result of the cleaning operation.
 */
export class CleanupResult {
    constructor() {
        this.totalFreeBytes = 0;
        this.errors = [];
        this.errorMessage = null;
    }

    /**
     * Whether the cleanup operation managed to
     * free some space.
     * @returns {boolean}
     */
    get success() {
        return this.totalFreeBytes > 0;
    }
}
