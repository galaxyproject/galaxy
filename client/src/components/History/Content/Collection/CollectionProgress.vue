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
            const failed = this.summary.get("failed") || 0;
            const error = this.summary.get("error") || 0;
            return failed + error;
        },
        waitingJobs() {
            const queued = this.summary.get("queued") || 0;
            const waiting = this.summary.get("waiting") || 0;
            return queued + waiting;
        },
    },
};
</script>
