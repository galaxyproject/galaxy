<script setup lang="ts">
import { computed, ref } from "vue";

import localize from "@/utils/localization";

import { DEFAULT_QUOTA_SOURCE_LABEL, type QuotaUsage } from "./model/QuotaUsage";

interface QuotaUsageBarProps {
    quotaUsage: QuotaUsage;
    embedded?: boolean;
    compact?: boolean;
}

const props = withDefaults(defineProps<QuotaUsageBarProps>(), {
    embedded: false,
    compact: false,
});

const storageSourceText = ref(localize("存储来源"));
const percentOfDiskQuotaUsedText = ref(localize("% 的磁盘配额已使用"));


const isDefaultQuota = computed(() => {
    return props.quotaUsage.sourceLabel === DEFAULT_QUOTA_SOURCE_LABEL;
});
const quotaHasLimit = computed(() => {
    return !props.quotaUsage.isUnlimited;
});
const progressVariant = computed(() => {
    const percent = props.quotaUsage.quotaPercent;
    if (percent === undefined || percent === null) {
        return "secondary";
    }
    if (percent < 50) {
        return "success";
    } else if (percent >= 50 && percent < 80) {
        return "primary";
    } else if (percent >= 80 && percent < 95) {
        return "warning";
    }
    return "danger";
});

const sourceTag = computed(() => {
    return props.embedded ? "div" : "h2";
});

const usageTag = computed(() => {
    return props.embedded ? "div" : "h3";
});

defineExpose({
    isDefaultQuota,
    quotaHasLimit,
});
</script>

<template>
    <div class="quota-usage-bar mx-auto" :class="{ 'w-75': !embedded, 'my-5': !embedded, 'my-1': embedded }">
        <component :is="sourceTag" v-if="!isDefaultQuota && !embedded" class="quota-storage-source">
            <span class="storage-source-label">
                <b>{{ quotaUsage.sourceLabel }}</b>
            </span>
            {{ storageSourceText }}
        </component>
        <component
            :is="usageTag"
            v-if="!compact"
            :data-quota-usage="quotaUsage.totalDiskUsageInBytes"
            class="quota-usage">
            <b>{{ quotaUsage.niceTotalDiskUsage }}</b>
            <span v-if="quotaHasLimit"> of {{ quotaUsage.niceQuota }}</span> used
        </component>
        <span v-if="quotaHasLimit && !compact" class="quota-percent-text" :data-quota-percent="quotaUsage.quotaPercent">
            {{ quotaUsage.quotaPercent }}{{ percentOfDiskQuotaUsedText }}
        </span>
        <b-progress
            v-if="quotaHasLimit || !(embedded || compact)"
            :value="quotaUsage.quotaPercent"
            :variant="progressVariant"
            max="100" />
    </div>
</template>
