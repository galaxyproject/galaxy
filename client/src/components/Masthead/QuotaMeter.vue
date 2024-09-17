<script setup lang="ts">
import { BLink, BProgress, BProgressBar } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { isRegisteredUser } from "@/api";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { bytesToString } from "@/utils/utils";

const { config } = useConfig();
const { currentUser, isAnonymous } = storeToRefs(useUserStore());

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

const quotaTitle = computed(() =>
    isAnonymous.value ? "Login to Access Storage Details" : "Storage and Usage Details"
);

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
    <div v-b-tooltip.hover.bottom class="quota-meter d-flex align-items-center" :title="quotaTitle">
        <BLink class="quota-progress" :to="quotaLink" data-description="storage dashboard link">
            <BProgress :max="100">
                <BProgressBar aria-label="Quota usage" :value="usage" :variant="variant" />
            </BProgress>
            <span>
                <span v-localize>Using</span>
                <span v-if="hasQuota">
                    <span>{{ usage.toFixed(0) }}%</span>
                    <span v-if="quotaLimit !== null">of {{ quotaLimit }}</span>
                </span>
                <span v-else>{{ totalUsageString }}</span>
            </span>
        </BLink>
    </div>
</template>

<style lang="scss" scoped>
.quota-meter {
    position: relative;
    height: 100%;
    margin-left: 0.5rem;
    margin-right: 0.5rem;
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
