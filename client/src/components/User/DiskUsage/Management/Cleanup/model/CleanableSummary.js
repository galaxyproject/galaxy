import { bytesToString } from "utils/utils";

/**
 * Contains summary information about how much storage space can be recovered by removing
 * a collection of items from it.
 */
export class CleanableSummary {
    constructor(data) {
        this._totalSize = data.totalSize;
        this._totalItems = data.totalItems;
    }

    /**
     * The total size in bytes that can be recovered by removing all the items.
     * @returns {Number}
     */
    get totalSize() {
        return this._totalSize;
    }

    /**
     * The human readable total amount of disk space that can be recovered.
     * @returns {String}
     */
    get niceTotalSize() {
        return bytesToString(this.totalSize, true);
    }

    /**
     * The total number of items that could be removed.
     */
    get totalItems() {
        return this._totalItems;
    }
}
