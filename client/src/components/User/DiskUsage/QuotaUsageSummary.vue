<template>
    <div class="quota-summary">
        <h2 class="text-center my-3">
            You've got <b>{{ totalQuotaString }}</b> of disk quota.
        </h2>
        <h4 class="text-center my-3">
            {{ quotaDescriptionSummary }}
        </h4>

        <div class="m-5">
            <h4>
                <b>{{ usedQuotaString }}</b> of {{ totalQuotaString }} used
            </h4>
            <h6>{{ usedQuotaPercent }}% of total disk quota used</h6>
            <b-progress :value="usedQuotaPercent" max="100"></b-progress>
        </div>
        <h4 class="text-center my-3">
            {{ quotaUsageHelp }}
        </h4>
        <b-row class="justify-content-md-center mb-3">
            <b-button :href="quotaSettings.quotasHelpUrl" target="_blank" variant="primary">
                Go to documentation
            </b-button>
        </b-row>
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
            quotaDescriptionSummary: _l("This is the maximum disk space that you can use."),
            quotaUsageHelp: _l(
                "Is your usage more than expected? See the documentation" +
                    " for tips on how to find all of the data in your account."
            ),
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
    },
};
</script>
