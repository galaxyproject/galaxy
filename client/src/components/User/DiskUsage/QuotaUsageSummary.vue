<template>
    <div class="quota-summary">
        <h2 class="text-center mt-5">
            You've got <b>{{ totalQuotaString }}</b> of disk quota.
        </h2>
        <h4 class="text-center mb-5">
            {{ quotaDescriptionSummary }}
        </h4>

        <div class="w-75 mx-auto my-5">
            <h3>
                <b>{{ usedQuotaString }}</b> of {{ totalQuotaString }} used
            </h3>
            <h5>{{ usedQuotaPercent }}% of total disk quota used</h5>
            <b-progress :value="usedQuotaPercent" :variant="progressVariant" max="100"></b-progress>
        </div>
    </div>
</template>

<script>
import _l from "utils/localization";
import { bytesToString } from "utils/utils";
import { QuotaSettings } from "./model";

export default {
    props: {
        user: {
            type: Object,
            required: true,
        },
        quotaSettings: {
            type: QuotaSettings,
            required: true,
        },
    },
    data() {
        return {
            quotaDescriptionSummary: _l("This is the maximum disk space that you can use"),
        };
    },
    computed: {
        /** @returns {String} */
        totalQuotaString() {
            return this.user.quota;
        },
        /** @returns {String} */
        usedQuotaString() {
            return bytesToString(this.user.total_disk_usage, true);
        },
        /** @returns {float} */
        usedQuotaPercent() {
            return this.user.quota_percent;
        },
        /** @returns {String} */
        progressVariant() {
            const percent = this.usedQuotaPercent;
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
