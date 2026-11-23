<script setup lang="ts">
import { BProgress, BProgressBar } from "bootstrap-vue";
import { computed, ref } from "vue";

import { useQuotaSourceNames } from "@/composables/quotaSourceNames";
import localize from "@/utils/localization";

import type { QuotaUsage } from "./model/QuotaUsage";

interface QuotaUsageBarProps {
    quotaUsage: QuotaUsage;
    embedded?: boolean;
    compact?: boolean;
    /** Name the default source too, as when it is shown among others */
    showDefaultSourceName?: boolean;
}

const props = withDefaults(defineProps<QuotaUsageBarProps>(), {
    embedded: false,
    compact: false,
    showDefaultSourceName: false,
});

const { quotaSourceName } = useQuotaSourceNames();
const sourceName = computed(() => quotaSourceName(props.quotaUsage.rawSourceLabel));

const percentOfDiskQuotaUsedText = ref(localize("% of disk quota used"));

const isDefaultQuota = computed(() => {
    return props.quotaUsage.rawSourceLabel === null;
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
    <div
        class="quota-usage-bar mx-auto"
        :quota-source-label="quotaUsage.rawSourceLabel"
        :class="{ 'w-75': !embedded, 'my-5': !embedded, 'my-1': embedded }">
        <component
            :is="sourceTag"
            v-if="!embedded && (!isDefaultQuota || showDefaultSourceName)"
            class="quota-storage-source">
            <span class="storage-source-label">
                <b>{{ sourceName }}</b>
            </span>
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
        <BProgress v-if="quotaHasLimit || !(embedded || compact)" max="100">
            <BProgressBar
                :value="quotaUsage.quotaPercent"
                :variant="progressVariant"
                :aria-label="`${sourceName} disk quota used`" />
        </BProgress>
    </div>
</template>
