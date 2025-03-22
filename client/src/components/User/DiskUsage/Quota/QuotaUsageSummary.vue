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
                <h2>您拥有<b>无限</b>磁盘配额</h2>
                <h3 v-localize class="h-sm">您的所有存储源都拥有无限磁盘空间。尽情享用吧！</h3>
            </div>
            <div v-else>
                <h2>
                    您拥有总计 <b>{{ niceTotalQuota }}</b> 的磁盘配额
                </h2>
                <h3 v-localize class="h-sm">
                    这是您可以在所有存储源中使用的最大磁盘空间。未计入无限存储源
                </h3>
            </div>
        </div>

        <div v-for="quotaUsage in props.quotaUsages" :key="quotaUsage.sourceLabel">
            <QuotaUsageBar :quota-usage="quotaUsage" class="quota-usage-bar" />
        </div>
    </div>
</template>
