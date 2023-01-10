import { bytesToString } from "@/utils/utils";

interface SummaryDataResponse {
    totalSize: number;
    totalItems: number;
}

/**
 * Contains summary information about how much storage space can be recovered by removing
 * a collection of items from it.
 */
export class CleanableSummary {
    private _data: SummaryDataResponse;

    constructor(data: SummaryDataResponse) {
        this._data = data;
    }

    /**
     * The total size in bytes that can be recovered by removing all the items.
     * @returns {Number}
     */
    get totalSize(): number {
        return this._data.totalSize;
    }

    /**
     * The human readable total amount of disk space that can be recovered.
     * @returns {String}
     */
    get niceTotalSize(): string {
        return bytesToString(this.totalSize, true, undefined);
    }

    /**
     * The total number of items that could be removed.
     */
    get totalItems() {
        return this._data.totalItems;
    }
}
