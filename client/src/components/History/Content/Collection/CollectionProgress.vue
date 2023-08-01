<!-- Job state progress bar for a collection. There's another similar component
at components/JobStates/CollectionJobStates but it relies on the backbone data
model, so probably has to go eventually.-->
<template>
    <div class="collection-progress">
        <GProgress v-if="!summary.isTerminal" :max="summary.jobCount">
            <GProgressBar
                v-if="summary.errorCount"
                v-b-tooltip.hover="summary.errorCountText"
                :value="summary.errorCount"
                variant="danger" />
            <GProgressBar
                v-if="summary.okCount"
                v-b-tooltip.hover="summary.okCountText"
                :value="summary.okCount"
                variant="success" />
            <GProgressBar
                v-if="summary.runningCount"
                v-b-tooltip.hover="summary.runningCountText"
                :value="summary.runningCount"
                variant="warning" />
            <GProgressBar
                v-if="summary.waitingCount"
                v-b-tooltip.hover="summary.waitingCountText"
                :value="summary.waitingCount"
                variant="secondary" />
        </GProgress>
    </div>
</template>
<script>
import { GProgress, GProgressBar } from "@/component-library";

import { JobStateSummary } from "./JobStateSummary";

export default {
    components: {
        GProgress,
        GProgressBar,
    },
    props: {
        summary: { type: JobStateSummary, required: true },
    },
};
</script>
