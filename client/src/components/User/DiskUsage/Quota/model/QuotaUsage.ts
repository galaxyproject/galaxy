import { type components } from "@/api/schema";
import { bytesToString } from "@/utils/utils";

export const DEFAULT_QUOTA_SOURCE_LABEL = "Default";

export type UserQuotaUsageData = components["schemas"]["UserQuotaUsage"];

/**
 * Contains information about quota usage for a particular ObjectStore.
 */
export class QuotaUsage {
    private _data: UserQuotaUsageData;

    constructor(data: UserQuotaUsageData) {
        this._data = data;
    }

    get rawSourceLabel(): string | null {
        return this._data.quota_source_label ?? null;
    }

    /**
     * The name of the ObjectStore associated with the quota.
     */
    get sourceLabel(): string {
        return this.rawSourceLabel ?? DEFAULT_QUOTA_SOURCE_LABEL;
    }

    /**
     * The maximum allowed disk usage in bytes.
     */
    get quotaInBytes(): number | undefined | null {
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
    get quotaPercent(): number | undefined | null {
        return this._data.quota_percent;
    }

    /**
     * The maximum allowed disk usage as human readable size.
     */
    get niceQuota(): string {
        if (this.isUnlimited) {
            return "unlimited";
        }
        if (this.quotaInBytes !== undefined && this.quotaInBytes !== null) {
            return bytesToString(this.quotaInBytes, true, undefined);
        }
        return "unknown";
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
