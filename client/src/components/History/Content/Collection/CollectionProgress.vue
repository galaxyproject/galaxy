<!-- Job state progress bar for a collection. There's another similar component
at components/JobStates/CollectionJobStates but it relies on the backbone data
model, so probably has to go eventually.-->
<template>
    <div class="collection-progress">
        <b-progress v-if="!summary.isTerminal" :max="summary.jobCount">
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
        </b-progress>
    </div>
</template>
<script>
import { JobStateSummary } from "./JobStateSummary";

import GProgressBar from "@/component-library/GProgressBar.vue";

export default {
    components: {
        GProgressBar,
    },
    props: {
        summary: { type: JobStateSummary, required: true },
    },
};
</script>
