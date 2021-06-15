<!-- Job state progress bar for a collection. There's another similar component
at components/JobStates/CollectionJobStates but it relies on the backbone data
model, so probably has to go eventually.-->

<template>
    <b-progress v-if="maxJobs && runningJobs" :max="maxJobs" height="1em">
        <b-progress-bar v-if="errorJobs" :value="errorJobs" variant="danger"></b-progress-bar>
        <b-progress-bar v-if="okJobs" :value="okJobs" variant="success"></b-progress-bar>
        <b-progress-bar v-if="runningJobs" :value="runningJobs" variant="info" animated></b-progress-bar>
        <b-progress-bar v-if="waitingJobs" :value="waitingJobs" variant="dark" animated></b-progress-bar>
    </b-progress>
</template>

<script>
import { JobStateSummary } from "../../model";

export default {
    props: {
        summary: { type: JobStateSummary, required: true },
    },
    computed: {
        hasRunningJobs() {
            return this.summary && this.summary.running > 0;
        },
        maxJobs() {
            return this.summary.all_jobs;
        },
        okJobs() {
            return this.summary.ok;
        },
        runningJobs() {
            return this.summary.running;
        },
        errorJobs() {
            const { failed = 0, error = 0 } = this.summary;
            return failed + error;
        },
        waitingJobs() {
            const { waiting = 0, queued = 0 } = this.summary;
            return waiting + queued;
        },
    },
};
</script>
