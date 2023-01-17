import { bytesToString } from "@/utils/utils";

export const DEFAULT_QUOTA_SOURCE_LABEL = "Default";

export interface QuotaUsageResponse {
    quota_source_label?: string;
    quota_bytes?: number;
    total_disk_usage: number;
    quota_percent?: number;
}

/**
 * Contains information about quota usage for a particular ObjectStore.
 */
export class QuotaUsage {
    private _data: QuotaUsageResponse;

    constructor(data: QuotaUsageResponse) {
        this._data = data;
    }

    /**
     * The name of the ObjectStore associated with the quota.
     */
    get sourceLabel(): string {
        return this._data.quota_source_label ?? DEFAULT_QUOTA_SOURCE_LABEL;
    }

    /**
     * The maximum allowed disk usage in bytes.
     */
    get quotaInBytes(): number | undefined {
        return this._data.quota_bytes;
    }

    /**
     * The total amount of bytes used in this ObjectStore.
     */
    get totalDiskUsageInBytes(): number {
        return this._data.total_disk_usage;
    }

    /**
     * The percentage of used quota.
     */
    get quotaPercent(): number | undefined {
        return this._data.quota_percent;
    }

    /**
     * The maximum allowed disk usage as human readable size.
     */
    get niceQuota(): string {
        if (this.isUnlimited) {
            return "unlimited";
        }
        return bytesToString(this.quotaInBytes, true, undefined);
    }

    /**
     * The total amount of disk used in this ObjectStore as human readable size.
     */
    get niceTotalDiskUsage(): string {
        return bytesToString(this.totalDiskUsageInBytes, true, undefined);
    }

    /**
     * Whether this ObjectStore has unlimited quota
     */
    get isUnlimited(): boolean {
        return !this.quotaInBytes;
    }
}
