<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import type { QuotaUsage } from "@/components/User/DiskUsage/Quota/model";
import { useQuotaSourceNames } from "@/composables/quotaSourceNames";
import { sourceLabelToKey } from "@/stores/quotaUsageStore";
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";
import QuotaUsageBar from "@/components/User/DiskUsage/Quota/QuotaUsageBar.vue";

defineProps<{
    /** Id of the element the popover opens from */
    target: string;
    quotaUsages?: QuotaUsage[];
    /** The server gives anonymous users no usage per source: they only get the default one and a way to log in */
    isAnonymous?: boolean;
    /** Whether the user exceeded the quota of the default storage */
    isOverQuota?: boolean;
}>();

const { quotaSourceName } = useQuotaSourceNames();

// The popover keeps its content mounted while hidden: list the sources only once open, since naming them loads
// the storages.
const isShown = ref(false);

function usageText(usage: QuotaUsage): string {
    if (usage.isUnlimited) {
        return `${usage.niceTotalDiskUsage} (${localize("unlimited")})`;
    }
    return `${usage.niceTotalDiskUsage} ${localize("of")} ${usage.niceQuota}`;
}
</script>

<template>
    <GPopover
        v-model:show="isShown"
        interactive
        :target="target"
        triggers="hover"
        placement="bottom"
        :title="localize('Storage usage')"
        custom-class="quota-sources-popover">
        <template v-if="isAnonymous">
            <div v-if="isOverQuota" class="text-danger small mb-2" data-description="anonymous over quota">
                <FontAwesomeIcon :icon="faExclamationTriangle" />
                {{ localize("Over quota on the default storage: jobs writing there are on hold") }}
            </div>
            <p class="mb-2" data-description="log in for storage usage">
                {{ localize("Log in to see your usage and quota on each storage.") }}
            </p>
            <GButton class="w-100" color="blue" size="small" to="/login/start" data-description="log in button">
                {{ localize("Log in") }}
            </GButton>
        </template>
        <ul v-else-if="isShown" class="list-unstyled mb-2">
            <li
                v-for="usage in quotaUsages"
                :key="sourceLabelToKey(usage.rawSourceLabel)"
                class="quota-source mb-2"
                :class="{ 'over-quota': usage.isOverQuota }"
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
        <GButton
            v-if="!isAnonymous"
            class="w-100"
            color="blue"
            size="small"
            to="/storage"
            data-description="storage dashboard button">
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
