<template>
    <div class="quota-summary">
        <div class="text-center my-5">
            <div v-if="allSourcesUnlimited">
                <h2>You've got <b>unlimited</b> disk quota</h2>
                <h4 v-localize>All your storage sources have unlimited disk space. Enjoy!</h4>
            </div>
            <div v-else>
                <h2>
                    You've got <b> {{ niceTotalQuota }} </b> of total disk quota
                </h2>
                <h4 v-localize>
                    This is the maximum disk space that you can use across all your storage sources. Unlimited storage
                    sources are not taken into account
                </h4>
            </div>
        </div>

        <div v-for="quotaUsage in quotaUsages" :key="quotaUsage.sourceLabel">
            <QuotaUsageBar :quota-usage="quotaUsage" />
        </div>
    </div>
</template>

<script>
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
    computed: {
        /** @returns {Number} */
        totalQuota() {
            const totalQuota = this.quotaUsages.reduce((acc, item) => acc + item.quotaInBytes, 0);
            return totalQuota;
        },
        /** @returns {String} */
        niceTotalQuota() {
            return bytesToString(this.totalQuota, true);
        },
        /** @returns {Boolean} */
        allSourcesUnlimited() {
            const allUnlimited = this.quotaUsages.every((usage) => usage.isUnlimited);
            return allUnlimited;
        },
    },
};
</script>
