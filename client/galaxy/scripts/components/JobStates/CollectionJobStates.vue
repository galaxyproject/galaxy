<template>
    <div v-if="!jobSourceType || jobSourceType == 'Job' || isTerminal">
        {{ simpleDescription }}
    </div>
    <div v-else-if="!jobStatesSummary || !jobStatesSummary.hasDetails()">
        <progress-bar :note="loadingNote" :loading="true" :infoProgress="1" />
    </div>
    <div v-else-if="isNew">
        <progress-bar note="Creating jobs" :loading="true" :infoProgress="1" />
    </div>
    <div v-else-if="isErrored">
        {{ errorDescription }}
    </div>
    <div v-else>
        <progress-bar
            :note="generatingNote"
            :okProgress="okPercent"
            :runningProgress="runningPercent"
            :newProgress="otherPercent"
        />
    </div>
</template>
<script>
import DC_VIEW from "mvc/collection/collection-view";
import mixin from "./mixin";
import ProgressBar from "components/ProgressBar";

export default {
    props: {
        collection: { type: Object, required: true }, // backbone model
        jobStatesSummary: { required: true }
    },
    components: {
        ProgressBar
    },
    mixins: [mixin],
    computed: {
        loadingNote() {
            return `Loading job data for ${this.collectionTypeDescription}}`;
        },
        generatingNote() {
            return `${this.jobsStr} generating a ${this.collectionTypeDescription}`;
        },
        jobSourceType() {
            return this.collection.get("job_source_type");
        },
        collectionTypeDescription() {
            return DC_VIEW.collectionTypeDescription(this.collection);
        },
        simpleDescription() {
            return DC_VIEW.collectionDescription(this.collection);
        },
        errorDescription() {
            var jobCount = this.jobCount;
            var errorCount = this.jobStatesSummary.numInError();
            return `a ${this.collectionTypeDescription} with ${errorCount} / ${jobCount} jobs in error`;
        }
    }
};
</script>
