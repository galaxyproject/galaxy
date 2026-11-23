<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { QuotaUsage } from "@/components/User/DiskUsage/Quota/model";
import { useQuotaSourceNames } from "@/composables/quotaSourceNames";
import { sourceLabelToKey } from "@/stores/quotaUsageStore";
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";
import QuotaUsageBar from "@/components/User/DiskUsage/Quota/QuotaUsageBar.vue";

defineProps<{
    quotaUsages: QuotaUsage[];
    /** The popover keeps its content mounted while hidden: naming the sources loads the storages, so wait until open. */
    showSources: boolean;
}>();

const { quotaSourceName } = useQuotaSourceNames();

function usageText(usage: QuotaUsage): string {
    if (usage.isUnlimited) {
        return `${usage.niceTotalDiskUsage} (${localize("unlimited")})`;
    }
    return `${usage.niceTotalDiskUsage} ${localize("of")} ${usage.niceQuota}`;
}
</script>

<template>
    <div>
        <ul v-if="showSources" class="list-unstyled mb-2">
            <li
                v-for="usage in quotaUsages"
                :key="sourceLabelToKey(usage.rawSourceLabel)"
                class="quota-source mb-2"
                data-description="quota source usage">
                <div class="d-flex justify-content-between">
                    <span class="font-weight-bold" data-description="quota source name">{{
                        quotaSourceName(usage.rawSourceLabel)
                    }}</span>
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
    </div>
</template>
