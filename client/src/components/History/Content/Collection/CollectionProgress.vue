<!-- Job state progress bar for a collection. There's another similar component
at components/JobStates/CollectionJobStates but it relies on the backbone data
model, so probably has to go eventually.-->
<template>
    <div class="collection-progress">
        <b-progress v-if="!summary.isTerminal" :max="summary.jobCount">
            <b-progress-bar
                v-if="summary.errorCount"
                :value="summary.errorCount"
                variant="danger"
                v-b-tooltip.hover="summary.errorCount" />
            <b-progress-bar
                v-if="summary.okCount"
                :value="summary.okCount"
                variant="success"
                v-b-tooltip.hover="summary.okCount" />
            <b-progress-bar
                v-if="summary.runningCount"
                :value="summary.runningCount"
                variant="warning"
                v-b-tooltip.hover="summary.runningCount" />
            <b-progress-bar
                v-if="summary.waitingCount"
                :value="summary.waitingCount"
                variant="secondary"
                v-b-tooltip.hover="summary.waitingCount" />
        </b-progress>
    </div>
</template>
<script>
import { JobStateSummary } from "./JobStateSummary";

export default {
    props: {
        summary: { type: JobStateSummary, required: true },
    },
};
</script>
