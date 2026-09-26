<script setup lang="ts">
import { BBadge } from "bootstrap-vue";
import { computed, ref } from "vue";

import { bytesToString } from "@/utils/utils";

import Popper from "@/components/Popper/Popper.vue";

interface Props {
    storeLabel: string;
    currentUsageBytes: number;
    deltaBytes: number;
    quotaLimitBytes?: number | null;
    scaleMaxBytes: number;
    isTargetStore?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    isTargetStore: false,
    quotaLimitBytes: null,
});

const barReference = ref<HTMLElement | null>(null);

// deltaBytes is a usage delta: negative means less used space (quota gain), positive means more used space (quota loss).
const isGain = computed(() => props.deltaBytes < 0);

const projectedUsageBytes = computed(() => Math.max(0, props.currentUsageBytes + props.deltaBytes));

const percentBaselineBytes = computed(() => {
    if (props.quotaLimitBytes && props.quotaLimitBytes > 0) {
        return props.quotaLimitBytes;
    }
    return props.scaleMaxBytes;
});

const formattedDelta = computed(() => {
    const sign = isGain.value ? "+" : "-";
    return `${sign}${bytesToString(Math.abs(props.deltaBytes))}`;
});

const currentPercent = computed(() => {
    if (percentBaselineBytes.value <= 0) {
        return 0;
    }
    return Math.min(100, (props.currentUsageBytes / percentBaselineBytes.value) * 100);
});

const projectedPercent = computed(() => {
    if (percentBaselineBytes.value <= 0) {
        return 0;
    }
    return Math.min(100, (projectedUsageBytes.value / percentBaselineBytes.value) * 100);
});

const deltaStartPercent = computed(() => {
    return isGain.value ? projectedPercent.value : currentPercent.value;
});

const deltaWidthPercent = computed(() => {
    return Math.max(0, Math.abs(projectedPercent.value - currentPercent.value));
});

const deltaChangePercentOfCurrent = computed(() => {
    if (props.quotaLimitBytes && props.quotaLimitBytes > 0) {
        return (Math.abs(props.deltaBytes) / props.quotaLimitBytes) * 100;
    }

    if (props.currentUsageBytes <= 0) {
        return 0;
    }

    return (Math.abs(props.deltaBytes) / props.currentUsageBytes) * 100;
});
</script>

<template>
    <div class="storage-quota-impact-bar py-2">
        <div class="d-flex align-items-center mb-1">
            <span class="small text-muted font-weight-bold">{{ props.storeLabel }}</span>
            <BBadge v-if="props.isTargetStore" variant="info" class="ml-2">Target</BBadge>
        </div>

        <div
            ref="barReference"
            class="quota-usage-bar"
            role="img"
            tabindex="0"
            :aria-label="`${props.storeLabel} usage change`">
            <div class="quota-usage-current" :style="{ width: `${currentPercent}%` }"></div>
            <div
                class="quota-usage-delta"
                :class="{ gain: isGain, loss: !isGain }"
                :style="{ left: `${deltaStartPercent}%`, width: `${deltaWidthPercent}%` }"></div>
        </div>

        <Popper v-if="barReference" :reference-el="barReference || undefined" placement="right-end" mode="light">
            <div class="p-2">
                <div class="font-weight-bold mb-1">{{ props.storeLabel }}</div>

                <div class="d-flex justify-content-between">
                    <span class="text-muted mr-2">Current</span>
                    <span>{{ bytesToString(props.currentUsageBytes) }}</span>
                </div>

                <div v-if="props.quotaLimitBytes" class="d-flex justify-content-between">
                    <span class="text-muted mr-2">Quota Limit</span>
                    <span>{{ bytesToString(props.quotaLimitBytes) }}</span>
                </div>

                <hr class="my-2" />

                <div class="d-flex justify-content-between">
                    <span class="text-muted mr-2">After Change</span>
                    <span>{{ bytesToString(projectedUsageBytes) }}</span>
                </div>

                <div class="d-flex justify-content-between mt-1">
                    <span class="text-muted mr-2">{{ isGain ? "Gain" : "Loss" }}</span>
                    <span>
                        {{ formattedDelta }}
                        ({{ deltaChangePercentOfCurrent.toFixed(2) }}%)
                    </span>
                </div>
            </div>
        </Popper>
    </div>
</template>

<style lang="scss" scoped>
@import "bootstrap/scss/_functions.scss";
@import "@/style/scss/theme/blue.scss";

.storage-quota-impact-bar + .storage-quota-impact-bar {
    border-top: 1px solid $border-color;
}

.quota-usage-bar {
    position: relative;
    height: 0.85rem;
    width: 100%;
    background: $gray-300;
    border-radius: 999px;
    overflow: hidden;
}

.quota-usage-current {
    height: 100%;
    background: $gray-600;
}

.quota-usage-delta {
    position: absolute;
    top: 0;
    height: 100%;
    min-width: 2px;
}

.quota-usage-delta.gain {
    background: theme-color("success");
    opacity: 0.85;
}

.quota-usage-delta.loss {
    background: theme-color("warning");
    opacity: 0.9;
}
</style>
