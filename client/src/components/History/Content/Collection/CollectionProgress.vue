<script setup lang="ts">
import { BProgress, BProgressBar } from "bootstrap-vue";

const props = defineProps<{
    summary: {
        isTerminal: boolean;
        jobCount: number;
        errorCount: number;
        errorCountText: string;
        okCount: number;
        okCountText: string;
        runningCount: number;
        runningCountText: string;
        waitingCount: number;
        waitingCountText: string;
    };
}>();
</script>

<template>
    <div class="collection-progress">
        <BProgress v-if="!props.summary.isTerminal" :max="props.summary.jobCount">
            <BProgressBar
                v-if="props.summary.errorCount"
                v-b-tooltip.hover="props.summary.errorCountText"
                :value="props.summary.errorCount"
                variant="danger" />
            <BProgressBar
                v-if="props.summary.okCount"
                v-b-tooltip.hover="props.summary.okCountText"
                :value="props.summary.okCount"
                variant="success" />
            <BProgressBar
                v-if="props.summary.runningCount"
                v-b-tooltip.hover="props.summary.runningCountText"
                :value="props.summary.runningCount"
                variant="warning" />
            <BProgressBar
                v-if="props.summary.waitingCount"
                v-b-tooltip.hover="props.summary.waitingCountText"
                :value="props.summary.waitingCount"
                variant="secondary" />
        </BProgress>
    </div>
</template>
