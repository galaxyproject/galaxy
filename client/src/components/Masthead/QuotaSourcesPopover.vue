<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { QuotaUsage } from "@/components/User/DiskUsage/Quota/model";
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";
import QuotaUsageBar from "@/components/User/DiskUsage/Quota/QuotaUsageBar.vue";

defineProps<{
    /** Id of the element the popover opens from */
    target: string;
    quotaUsages?: QuotaUsage[];
}>();

function sourceName(usage: QuotaUsage): string {
    return usage.rawSourceLabel ?? localize("Default storage");
}

function sourceKey(usage: QuotaUsage): string {
    return usage.rawSourceLabel ?? "__default__";
}

function usageText(usage: QuotaUsage): string {
    if (usage.isUnlimited) {
        return `${usage.niceTotalDiskUsage} (${localize("unlimited")})`;
    }
    return `${usage.niceTotalDiskUsage} ${localize("of")} ${usage.niceQuota}`;
}
</script>

<template>
    <GPopover
        interactive
        :target="target"
        triggers="hover"
        placement="bottom"
        :title="localize('Storage usage')"
        custom-class="quota-sources-popover">
        <ul class="list-unstyled mb-2">
            <li
                v-for="usage in quotaUsages"
                :key="sourceKey(usage)"
                class="quota-source mb-2"
                :class="{ 'over-quota': usage.isOverQuota }"
                data-description="quota source usage">
                <div class="d-flex justify-content-between">
                    <span class="font-weight-bold" data-description="quota source name">{{ sourceName(usage) }}</span>
                    <span class="ml-3 text-nowrap">{{ usageText(usage) }}</span>
                </div>
                <QuotaUsageBar :quota-usage="usage" embedded compact />
                <div v-if="usage.isOverQuota" class="text-danger small" data-description="quota source over quota">
                    <FontAwesomeIcon :icon="faExclamationTriangle" />
                    {{ localize("Over quota: jobs writing here are on hold") }}
                </div>
            </li>
        </ul>
        <GButton class="w-100" color="blue" size="small" to="/storage" data-description="storage dashboard button">
            {{ localize("Open Storage Dashboard") }}
        </GButton>
    </GPopover>
</template>

<!-- Not scoped: the popover moves itself to the document body -->
<style lang="scss">
.quota-sources-popover {
    min-width: 18rem;
    max-width: 24rem;
}
</style>
