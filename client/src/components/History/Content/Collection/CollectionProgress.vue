<!-- Job state progress bar for a collection. There's another similar component
at components/JobStates/CollectionJobStates but it relies on the backbone data
model, so probably has to go eventually.-->
<script setup lang="ts">
import { type JobStateSummary } from "./JobStateSummary";

interface Props {
    summary: JobStateSummary;
}

defineProps<Props>();
</script>

<template>
    <div class="collection-progress">
        <BProgress v-if="!summary.isTerminal" :max="summary.jobCount">
            <BProgressBar
                v-if="summary.errorCount"
                v-b-tooltip.hover="summary.errorCountText"
                :value="summary.errorCount"
                variant="danger" />
            <BProgressBar
                v-if="summary.okCount"
                v-b-tooltip.hover="summary.okCountText"
                :value="summary.okCount"
                variant="success" />
            <BProgressBar
                v-if="summary.runningCount"
                v-b-tooltip.hover="summary.runningCountText"
                :value="summary.runningCount"
                variant="warning" />
            <BProgressBar
                v-if="summary.waitingCount"
                v-b-tooltip.hover="summary.waitingCountText"
                :value="summary.waitingCount"
                variant="secondary" />
        </BProgress>
    </div>
</template>
