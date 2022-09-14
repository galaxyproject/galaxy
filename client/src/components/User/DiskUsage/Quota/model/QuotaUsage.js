import { bytesToString } from "utils/utils";

export const DEFAULT_QUOTA_SOURCE_LABEL = "Default";

/**
 * Contains information about quota usage for a particular ObjectStore.
 */
export class QuotaUsage {
    constructor(data) {
        this._data = data;
    }

    /**
     * The name of the ObjectStore associated with the quota.
     * @returns {String}
     */
    get sourceLabel() {
        return this._data.quota_source_label || DEFAULT_QUOTA_SOURCE_LABEL;
    }

    /**
     * The maximum allowed disk usage in bytes.
     * @returns {Number}
     */
    get quotaInBytes() {
        return this._data.quota_bytes;
    }

    /**
     * The total amount of bytes used in this ObjectStore.
     * @returns {Number}
     */
    get totalDiskUsageInBytes() {
        return this._data.total_disk_usage;
    }

    /**
     * The percentage of used quota.
     * @returns {Number}
     */
    get quotaPercent() {
        return this._data.quota_percent;
    }

    /**
     * The maximum allowed disk usage as human readable size.
     * @returns {String}
     */
    get niceQuota() {
        if (this.isUnlimited) {
            return "unlimited";
        }
        return bytesToString(this.quotaInBytes, true);
    }

    /**
     * The total amount of disk used in this ObjectStore as human readable size.
     * @returns {String}
     */
    get niceTotalDiskUsage() {
        return bytesToString(this.totalDiskUsageInBytes, true);
    }

    /**
     * Whether this ObjectStore has unlimited quota
     * @returns {Boolean}
     */
    get isUnlimited() {
        return !this.quotaInBytes;
    }
}
