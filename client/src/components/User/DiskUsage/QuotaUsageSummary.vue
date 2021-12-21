<template>
    <div>
        <h2 class="text-center my-3">
            You've got <b>{{ quotaString }}</b> of disk quota.
        </h2>
        <h4 class="text-center my-3">
            {{ quotaDescriptionSummary }}
        </h4>

        <div class="m-5">
            <h4>{{ usedQuotaString }} of {{ quotaString }} used</h4>
            <b-progress :value="quotaPercent" :max="maxPercent"></b-progress>
        </div>
        <h4 class="text-center my-3">
            {{ quotaUsageHelp }}
        </h4>
        <b-row class="justify-content-md-center mb-3">
            <b-button :href="quotaDocumentationLink" target="_blank" variant="primary"> Go to documentation </b-button>
        </b-row>
    </div>
</template>

<script>
import _l from "utils/localization";
import { bytesToString } from "utils/utils";

export default {
    props: {
        user: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            quotaDescriptionSummary: _l("This is the maximum disk space that you can use."),
            quotaUsageHelp: _l(
                "Is your usage more than expected? See the documentation for tips on how to find all of the data in your account."
            ),
            quotaDocumentationLink: "https://galaxyproject.org/support/account-quotas/",
            maxPercent: 100,
        };
    },
    computed: {
        /** @returns {String} */
        quotaString() {
            return this.user.quota;
        },
        /** @returns {String} */
        usedQuotaString() {
            return bytesToString(this.user.total_disk_usage, true);
        },
        /** @returns {float} */
        quotaPercent() {
            return this.user.quota_percent;
        },
    },
};
</script>
