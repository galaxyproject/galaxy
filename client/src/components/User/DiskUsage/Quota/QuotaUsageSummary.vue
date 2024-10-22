<script setup lang="ts">
import { computed } from "vue";

import { bytesToString } from "@/utils/utils";

import { type QuotaUsage } from "./model";

import QuotaUsageBar from "./QuotaUsageBar.vue";

interface QuotaUsageSummaryProps {
    quotaUsages: QuotaUsage[];
}

const props = defineProps<QuotaUsageSummaryProps>();

const totalQuotaInBytes = computed(() => {
    const totalQuota = props.quotaUsages.reduce((acc, item) => acc + (item.quotaInBytes ?? 0), 0);
    return totalQuota;
});

const niceTotalQuota = computed(() => {
    return bytesToString(totalQuotaInBytes.value, true, undefined);
});

const allSourcesUnlimited = computed(() => {
    const allUnlimited = props.quotaUsages.every((usage) => usage.isUnlimited);
    return allUnlimited;
});

defineExpose({
    totalQuotaInBytes,
});
</script>

<template>
    <div class="quota-summary">
        <div class="text-center my-5">
            <div v-if="allSourcesUnlimited">
                <h2>You've got <b>unlimited</b> disk quota</h2>
                <h3 v-localize class="h-sm">All your storage sources have unlimited disk space. Enjoy!</h3>
            </div>
            <div v-else>
                <h2>
                    You've got <b> {{ niceTotalQuota }} </b> of total disk quota
                </h2>
                <h3 v-localize class="h-sm">
                    This is the maximum disk space that you can use across all your storage sources. Unlimited storage
                    sources are not taken into account
                </h3>
            </div>
        </div>

        <div v-for="quotaUsage in props.quotaUsages" :key="quotaUsage.sourceLabel">
            <QuotaUsageBar :quota-usage="quotaUsage" class="quota-usage-bar" />
        </div>
    </div>
</template>
