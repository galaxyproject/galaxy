<template>
    <div class="quota-usage-bar w-75 mx-auto my-5">
        <h2 v-if="!isDefaultQuota" class="quota-storage-source">
            <span class="storage-source-label">
                <b>{{ quotaUsage.sourceLabel }}</b>
            </span>
            {{ storageSourceText }}
        </h2>
        <h3>
            <b>{{ quotaUsage.niceTotalDiskUsage }}</b> of {{ quotaUsage.niceQuota }} used
        </h3>
        <span v-if="quotaHasLimit" class="quota-percent-text">
            {{ quotaUsage.quotaPercent }}{{ percentOfDiskQuotaUsedText }}
        </span>
        <b-progress :value="quotaUsage.quotaPercent" :variant="progressVariant" max="100" />
    </div>
</template>

<script>
import _l from "utils/localization";
import { DEFAULT_QUOTA_SOURCE_LABEL } from "./model/QuotaUsage";

export default {
    props: {
        quotaUsage: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            storageSourceText: _l("storage source"),
            percentOfDiskQuotaUsedText: _l("% of disk quota used"),
        };
    },
    computed: {
        /** @returns {Boolean} */
        isDefaultQuota() {
            return this.quotaUsage.sourceLabel === DEFAULT_QUOTA_SOURCE_LABEL;
        },
        /** @returns {Boolean} */
        quotaHasLimit() {
            return !this.quotaUsage.isUnlimited;
        },
        /** @returns {String} */
        progressVariant() {
            const percent = this.quotaUsage.quotaPercent;
            if (percent < 50) {
                return "success";
            } else if (percent >= 50 && percent < 80) {
                return "primary";
            } else if (percent >= 80 && percent < 95) {
                return "warning";
            }
            return "danger";
        },
    },
};
</script>
