<script setup lang="ts">
import { BPopover, BProgress, BProgressBar } from "bootstrap-vue";
import { computed } from "vue";

import localize from "@/utils/localization";

type ProgressHeightClass = "storage-operation-progress-sm" | "storage-operation-progress-md";

interface Props {
    totalCount: number;
    succeededCount: number;
    failedCount: number;
    skippedCount: number;
    heightClass?: ProgressHeightClass;
    showDetails?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    heightClass: "storage-operation-progress-sm",
    showDetails: true,
});

const processedCount = computed(() => props.succeededCount + props.failedCount + props.skippedCount);

const progressPercent = computed(() => {
    if (props.totalCount <= 0) {
        return 0;
    }
    return Math.min(100, Math.round((processedCount.value / props.totalCount) * 100));
});

const succeededPercent = computed(() => {
    if (props.totalCount <= 0) {
        return 0;
    }
    return Math.round((props.succeededCount / props.totalCount) * 100);
});

const failedPercent = computed(() => {
    if (props.totalCount <= 0) {
        return 0;
    }
    return Math.round((props.failedCount / props.totalCount) * 100);
});

const skippedPercent = computed(() => {
    if (props.totalCount <= 0) {
        return 0;
    }
    return Math.round((props.skippedCount / props.totalCount) * 100);
});

const progressLabel = computed(() => {
    return localize(`Progress: ${processedCount.value} / ${props.totalCount} (${progressPercent.value}%)`);
});

const popoverTargetId = `storage-operation-progress-${Math.random().toString(36).slice(2, 10)}`;
</script>

<template>
    <div>
        <div :id="popoverTargetId" class="storage-operation-progress-target">
            <BProgress :max="props.totalCount || 1" :class="props.heightClass" :aria-label="progressLabel">
                <BProgressBar variant="success" :value="props.succeededCount" />
                <BProgressBar variant="danger" :value="props.failedCount" />
                <BProgressBar variant="warning" :value="props.skippedCount" />
            </BProgress>
        </div>

        <BPopover
            v-if="props.showDetails"
            :target="popoverTargetId"
            triggers="hover focus"
            boundary="window"
            placement="top">
            <div class="storage-operation-progress-popover">
                <div>
                    <strong>{{ localize("Success") }}:</strong> {{ props.succeededCount }} ({{ succeededPercent }}%)
                </div>
                <div>
                    <strong>{{ localize("Failed") }}:</strong> {{ props.failedCount }} ({{ failedPercent }}%)
                </div>
                <div>
                    <strong>{{ localize("Skipped") }}:</strong> {{ props.skippedCount }} ({{ skippedPercent }}%)
                </div>
                <div class="text-muted mt-1">
                    <strong>{{ localize("Total Processed") }}:</strong> {{ processedCount }} /
                    {{ props.totalCount }} ({{ progressPercent }}%)
                </div>
            </div>
        </BPopover>
    </div>
</template>

<style scoped>
.storage-operation-progress-popover {
    min-width: 220px;
}

.storage-operation-progress-sm {
    height: 0.6rem;
}

.storage-operation-progress-md {
    height: 1rem;
}
</style>
