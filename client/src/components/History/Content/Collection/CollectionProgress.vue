<!-- Job state progress bar for a collection. There's another similar component
at components/JobStates/CollectionJobStates but it relies on the backbone data
model, so probably has to go eventually.-->
<template>
    <div class="collection-progress">
        <b-progress v-if="maxJobs != okJobs + errorJobs" :max="maxJobs">
            <b-progress-bar v-if="errorJobs" :value="errorJobs" variant="danger" v-b-tooltip.hover="errorJobs" />
            <b-progress-bar v-if="okJobs" :value="okJobs" variant="success" v-b-tooltip.hover="okJobs" />
            <b-progress-bar v-if="runningJobs" :value="runningJobs" variant="warning" v-b-tooltip.hover="runningJobs" />
            <b-progress-bar
                v-if="waitingJobs"
                :value="waitingJobs"
                variant="secondary"
                v-b-tooltip.hover="waitingJobs" />
        </b-progress>
    </div>
</template>
<script>
import { JobStateSummary } from "./JobStateSummary";

export default {
    props: {
        summary: { type: JobStateSummary, required: true },
    },
    computed: {
        maxJobs() {
            return this.summary.get("all_jobs");
        },
        okJobs() {
            return this.summary.get("ok");
        },
        runningJobs() {
            return this.summary.get("running");
        },
        errorJobs() {
            const failed = this.summary.get("failed") || 0;
            const error = this.summary.get("error") || 0;
            const discarded = this.summary.get("discarded") || 0;
            return failed + error + discarded;
        },
        waitingJobs() {
            const queued = this.summary.get("queued") || 0;
            const waiting = this.summary.get("waiting") || 0;
            const paused = this.summary.get("paused") || 0;
            return queued + waiting + paused;
        },
    },
};
</script>
