<!-- Dataset state progress bar for a collection. -->
<script setup lang="ts">
import type { DatasetStateSummary } from "./DatasetStateSummary";

interface Props {
    summary: DatasetStateSummary;
}

defineProps<Props>();
</script>

<template>
    <div class="dataset-progress">
        <BProgress v-if="!summary.isTerminal" :max="summary.datasetCount">
            <BProgressBar
                v-if="summary.errorCount"
                v-g-tooltip.hover="`${summary.errorCount} Error`"
                :value="summary.errorCount"
                variant="danger" />
            <BProgressBar
                v-if="summary.okCount"
                v-g-tooltip.hover="`${summary.okCount} OK`"
                :value="summary.okCount"
                variant="success" />
            <BProgressBar
                v-if="summary.runningCount"
                v-g-tooltip.hover="`${summary.runningCount} Running`"
                :value="summary.runningCount"
                variant="warning" />
            <BProgressBar
                v-if="summary.waitingCount"
                v-g-tooltip.hover="`${summary.waitingCount} Waiting`"
                :value="summary.waitingCount"
                variant="secondary" />
        </BProgress>
    </div>
</template>
