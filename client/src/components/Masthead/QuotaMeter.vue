<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink, BProgress, BProgressBar } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { isRegisteredUser, isUserOverQuota } from "@/api";
import { useConfig } from "@/composables/config";
import { useQuotaSourceNames } from "@/composables/quotaSourceNames";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { bytesToString } from "@/utils/utils";

import QuotaSourcesPopover from "./QuotaSourcesPopover.vue";

const { config } = useConfig();
const { currentUser, isAnonymous } = storeToRefs(useUserStore());
const { quotaUsages, otherSourcesOverQuota } = storeToRefs(useQuotaUsageStore());
const { otherSourcesOverQuotaNames } = useQuotaSourceNames();

const LINK_ID = "quota-meter-link";

const otherSourcesOverQuotaText = computed(
    () => `${localize("Over quota on these storages:")} ${otherSourcesOverQuotaNames.value}`,
);

// Only with quotas on several storages: other pages load the usage per storage even with quotas off. The server gives
// anonymous users no usage per storage, so for them the configured quota sources tell.
const showSourcesPopover = computed(() => {
    if (!config.value.enable_quotas) {
        return false;
    }
    if (isAnonymous.value) {
        return (config.value.quota_source_labels?.length ?? 0) > 0;
    }
    return (quotaUsages.value?.length ?? 0) > 1;
});
const isOverDefaultQuota = computed(() => isUserOverQuota(currentUser.value));

const hasQuota = computed<boolean>(() => {
    const quotasEnabled = config.value.enable_quotas ?? false;
    const quotaLimited = (isRegisteredUser(currentUser.value) && currentUser.value.quota !== "unlimited") ?? false;
    return quotasEnabled && quotaLimited;
});

const quotaLimit = computed(() => (isRegisteredUser(currentUser.value) && currentUser.value.quota) ?? null);

const totalUsageString = computed(() => {
    const total = currentUser.value?.total_disk_usage ?? 0;
    return bytesToString(total, true);
});

const usage = computed(() => {
    if (hasQuota.value) {
        return currentUser.value?.quota_percent ?? 0;
    }
    return currentUser.value?.total_disk_usage ?? 0;
});

const quotaLink = computed(() => (isAnonymous.value ? "/login/start" : "/storage"));

// The popover listing the sources takes the place of the tooltip. An empty title in the binding turns it off; a
// title attribute wouldn't, as the directive keeps showing the first one it saw.
const quotaTitle = computed(() => {
    if (showSourcesPopover.value) {
        return "";
    }
    return localize(isAnonymous.value ? "Login to Access Storage Details" : "Storage and Usage Details");
});

const variant = computed(() => {
    if (!hasQuota.value || usage.value < 80) {
        return "success";
    } else if (usage.value < 95) {
        return "warning";
    }
    return "danger";
});
</script>

<template>
    <div v-g-tooltip.hover.bottom="{ title: quotaTitle }" class="quota-meter d-flex align-items-center">
        <BLink :id="LINK_ID" class="quota-progress" :to="quotaLink" data-description="storage dashboard link">
            <BProgress :max="100">
                <BProgressBar aria-label="Quota usage" :value="usage" :variant="variant" />
            </BProgress>
            <span>
                <span v-localize>Using</span>{{ " "
                }}<span v-if="hasQuota"
                    ><span>{{ usage.toFixed(0) }}%</span>{{ " "
                    }}<span v-if="quotaLimit !== null">of {{ quotaLimit }}</span></span
                ><span v-else>{{ totalUsageString }}</span
                ><span
                    v-if="otherSourcesOverQuota.length"
                    class="other-sources-over-quota ml-1"
                    data-description="other storage over quota">
                    <FontAwesomeIcon :icon="faExclamationTriangle" />
                    <span class="sr-only">{{ otherSourcesOverQuotaText }}</span>
                </span>
            </span>
        </BLink>
        <QuotaSourcesPopover
            v-if="showSourcesPopover"
            :target="LINK_ID"
            :quota-usages="quotaUsages"
            :is-anonymous="isAnonymous"
            :is-over-default-quota="isOverDefaultQuota" />
    </div>
</template>

<style lang="scss" scoped>
.quota-meter {
    position: relative;
    height: 100%;
    margin-left: 0.5rem;
    margin-right: 0.5rem;
    .other-sources-over-quota {
        color: var(--color-yellow-500);
        // A dark outline keeps the icon visible on the light bar and on the red one alike
        filter: drop-shadow(0 0 0.5px var(--color-grey-900)) drop-shadow(0 0 0.5px var(--color-grey-900));
    }
    .quota-progress {
        width: 12rem;
        height: 1.4em;
        position: relative;
        & > * {
            position: absolute;
            width: 100%;
            height: 100%;
            text-align: center;
            line-height: 1.4em;
            pointer-events: none;
        }
    }
    :deep(a) {
        &:focus-visible {
            outline: 2px solid var(--masthead-text-hover);
        }
    }
}
</style>
