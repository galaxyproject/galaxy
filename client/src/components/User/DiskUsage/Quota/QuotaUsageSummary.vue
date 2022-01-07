<template>
    <div class="quota-summary">
        <div class="text-center my-5">
            <h2>
                You've got <b>{{ totalQuotaString }}</b> of total disk quota.
            </h2>
            <h4>
                {{ quotaDescriptionSummary }}
            </h4>
        </div>

        <div v-for="quotaUsage in quotaUsages" :key="quotaUsage.sourceLabel">
            <QuotaUsageBar :quota-usage="quotaUsage" />
        </div>
    </div>
</template>

<script>
import _l from "utils/localization";
import { bytesToString } from "utils/utils";
import QuotaUsageBar from "./QuotaUsageBar";

export default {
    components: {
        QuotaUsageBar,
    },
    props: {
        quotaUsages: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            quotaDescriptionSummary: _l(
                "This is the maximum disk space that you can use across all your storage sources." +
                    " Unlimited storage sources are not taken into account"
            ),
        };
    },
    computed: {
        /** @returns {String} */
        totalQuotaString() {
            const totalQuota = this.quotaUsages.reduce((acc, item) => acc + item.quotaInBytes, 0);
            return bytesToString(totalQuota, true);
        },
    },
};
</script>
