<!-- Job state progress bar for a collection. There's another similar component
at components/JobStates/CollectionJobStates but it relies on the backbone data
model, so probably has to go eventually.-->
<template>
    <div>
        <b-progress v-if="maxJobs && runningJobs" :max="maxJobs" height="1em" show-value>
            <b-progress-bar v-if="errorJobs" :value="errorJobs" variant="danger"></b-progress-bar>
            <b-progress-bar v-if="okJobs" :value="okJobs" variant="success"></b-progress-bar>
            <b-progress-bar v-if="runningJobs" :value="runningJobs" variant="info" animated></b-progress-bar>
            <b-progress-bar v-if="waitingJobs" :value="waitingJobs" variant="dark" animated></b-progress-bar>
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
        hasRunningJobs() {
            return this.summary && this.summary.get("running") > 0;
        },
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
