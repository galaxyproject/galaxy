import { type components } from "@/api/schema";
import { bytesToString } from "@/utils/utils";

type CleanableItemsSummaryResponse = components["schemas"]["CleanableItemsSummary"];

/**
 * Contains summary information about how much storage space can be recovered by removing
 * a collection of items from it.
 */
export class CleanableSummary {
    private _data: CleanableItemsSummaryResponse;

    constructor(data: CleanableItemsSummaryResponse) {
        this._data = data;
    }

    /**
     * The total size in bytes that can be recovered by removing all the items.
     */
    get totalSize(): number {
        return this._data.total_size;
    }

    /**
     * The human readable total amount of disk space that can be recovered.
     */
    get niceTotalSize(): string {
        return bytesToString(this.totalSize, true, undefined);
    }

    /**
     * The total number of items that could be removed.
     */
    get totalItems() {
        return this._data.total_items;
    }
}
