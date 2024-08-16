import { type components } from "@/api/schema";
import { bytesToString } from "@/utils/utils";

export const DEFAULT_QUOTA_SOURCE_LABEL = "Default";

export type UserQuotaUsageData = components["schemas"]["UserQuotaUsage"];

/**
 * Contains information about quota usage for a particular ObjectStore.
 */
export interface QuotaUsage {
    rawSourceLabel: string | null;

    /**
     * The name of the ObjectStore associated with the quota.
     */
    sourceLabel: string;

    /**
     * The maximum allowed disk usage in bytes.
     */
    quotaInBytes: number | undefined | null;

    /**
     * The total amount of bytes used in this ObjectStore.
     */
    totalDiskUsageInBytes: number;

    /**
     * The percentage of used quota.
     */
    quotaPercent: number | undefined | null;

    /**
     * The maximum allowed disk usage as human readable size.
     */
    niceQuota: string;

    /**
     * The total amount of disk used in this ObjectStore as human readable size.
     */
    niceTotalDiskUsage: string;

    /**
     * Whether this ObjectStore has unlimited quota
     */
    isUnlimited: boolean;
}

/**
 * Converts a raw UserQuotaUsageData response to a QuotaUsage object.
 * @param data The raw UserQuotaUsageData response.
 * @returns The QuotaUsage object.
 */
export function toQuotaUsage(data: UserQuotaUsageData): QuotaUsage {
    return new QuotaUsageModel(data);
}

class QuotaUsageModel implements QuotaUsage {
    private _data: UserQuotaUsageData;

    constructor(data: UserQuotaUsageData) {
        this._data = data;
    }

    get rawSourceLabel(): string | null {
        return this._data.quota_source_label ?? null;
    }

    get sourceLabel(): string {
        return this.rawSourceLabel ?? DEFAULT_QUOTA_SOURCE_LABEL;
    }

    get quotaInBytes(): number | undefined | null {
        return this._data.quota_bytes;
    }

    get totalDiskUsageInBytes(): number {
        return this._data.total_disk_usage;
    }

    get quotaPercent(): number | undefined | null {
        return this._data.quota_percent;
    }

    get niceQuota(): string {
        if (this.isUnlimited) {
            return "unlimited";
        }
        if (this.quotaInBytes !== undefined && this.quotaInBytes !== null) {
            return bytesToString(this.quotaInBytes, true, undefined);
        }
        return "unknown";
    }

    get niceTotalDiskUsage(): string {
        return bytesToString(this.totalDiskUsageInBytes, true, undefined);
    }

    get isUnlimited(): boolean {
        return !this.quotaInBytes;
    }
}
