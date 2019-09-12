<template>
    <div v-if="!jobSourceType || jobSourceType == 'Job' || isTerminal">
        {{ simpleDescription }}
    </div>
    <div v-else-if="!jobStatesSummary || !jobStatesSummary.hasDetails()">
        <div class="progress state-progress">
            <span class="note"
                >Loading job data for {{ collectionTypeDescription }}.<span class="blinking">..</span></span
            >
            <div class="progress-bar info" style="width:100%"></div>
        </div>
    </div>
    <div v-else-if="isNew">
        <div class="progress state-progress">
            <span class="note">Creating jobs.<span class="blinking">..</span></span>
            <div class="progress-bar info" style="width:100%"></div>
        </div>
    </div>
    <div v-else-if="isErrored">
        {{ errorDescription }}
    </div>
    <div v-else>
        <div class="progress state-progress">
            <span class="note">{{ jobsStr }} generating a {{ collectionTypeDescription }}</span>
            <div class="progress-bar ok" v-bind:style="okStyle"></div>
            <div class="progress-bar running" v-bind="runningStyle"></div>
            <div class="progress-bar new" v-bind:style="otherStyle"></div>
        </div>
    </div>
</template>
<script>
import DC_VIEW from "mvc/collection/collection-view";

export default {
    props: {
        collection: { type: Object, required: true }, // backbone model
        jobStatesSummary: { required: true }
    },
    computed: {
        jobSourceType() {
            return this.collection.get("job_source_type");
        },
        collectionTypeDescription() {
            return DC_VIEW.collectionTypeDescription(this.collection);
        },
        simpleDescription() {
            return DC_VIEW.collectionDescription(this.collection);
        },
        isNew() {
            return this.jobStatesSummary && this.jobStatesSummary.new();
        },
        isErrored() {
            return this.jobStatesSummary && this.jobStatesSummary.errored();
        },
        isTerminal() {
            return this.jobStatesSummary && this.jobStatesSummary.terminal();
        },
        jobCount() {
            return this.isNew ? null : this.jobStatesSummary.jobCount();
        },
        errorDescription() {
            var jobCount = this.jobCount;
            var errorCount = this.jobStatesSummary.numInError();
            return `a ${this.collectionTypeDescription} with ${errorCount} / ${jobCount} jobs in error`;
        },
        jobsStr() {
            const jobCount = this.jobCount;
            return jobCount && jobCount > 1 ? `${jobCount} jobs` : `a job`;
        },
        runningPercent() {
            const running = this.jobStatesSummary.states()["running"] || 0;
            return running / (this.jobCount * 1.0);
        },
        okPercent() {
            const ok = this.jobStatesSummary.states()["ok"] || 0;
            return ok / (this.jobCount * 1.0);
        },
        otherPercent() {
            return 1.0 - this.okPercent - this.runningPercent;
        },
        okStyle() {
            return { width: `${this.okPercent * 100}%` };
        },
        runningStyle() {
            return { width: `${this.runningPercent * 100}%` };
        },
        otherStyle() {
            return { width: `${this.otherPercent * 100}%` };
        }
    }
};
</script>
