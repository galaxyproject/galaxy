<script setup lang="ts">
import { computed, ref } from "vue";
import localize from "@/utils/localization";
import { DEFAULT_QUOTA_SOURCE_LABEL, QuotaUsage } from "./model/QuotaUsage";

interface QuotaUsageBarProps {
    quotaUsage: QuotaUsage;
}

const props = defineProps<QuotaUsageBarProps>();

const storageSourceText = ref(localize("storage source"));
const percentOfDiskQuotaUsedText = ref(localize("% of disk quota used"));

const isDefaultQuota = computed(() => {
    return props.quotaUsage.sourceLabel === DEFAULT_QUOTA_SOURCE_LABEL;
});
const quotaHasLimit = computed(() => {
    return !props.quotaUsage.isUnlimited;
});
const progressVariant = computed(() => {
    const percent = props.quotaUsage.quotaPercent;
    if (percent === undefined) {
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

defineExpose({
    isDefaultQuota,
    quotaHasLimit,
});
</script>

<template>
    <div class="quota-usage-bar w-75 mx-auto my-5">
        <h2 v-if="!isDefaultQuota" class="quota-storage-source">
            <span class="storage-source-label">
                <b>{{ quotaUsage.sourceLabel }}</b>
            </span>
            {{ storageSourceText }}
        </h2>
        <h3>
            <b>{{ quotaUsage.niceTotalDiskUsage }}</b>
            <span v-if="quotaHasLimit"> of {{ quotaUsage.niceQuota }}</span> used
        </h3>
        <span v-if="quotaHasLimit" class="quota-percent-text">
            {{ quotaUsage.quotaPercent }}{{ percentOfDiskQuotaUsedText }}
        </span>
        <b-progress :value="quotaUsage.quotaPercent" :variant="progressVariant" max="100" />
    </div>
</template>
