<template>
    <b-card>
        <JobInformation :job_id="id" :include-times="true">
            <!-- only needed for admin job component -->
            <tr v-if="hasTraceback">
                <td>Traceback</td>
                <td>
                    <CodeRow :code-label="'Traceback'" :code-item="job.traceback" />
                </td>
            </tr>
            <tr v-if="hasInfo">
                <td>Info</td>
                <td>
                    <CodeRow :code-label="'Info'" :code-item="job.info" />
                </td>
            </tr>
            <tr v-if="hasRemoteHost">
                <td>Remote Host</td>
                <td>
                    {{ job.remote_host }}
                </td>
            </tr>
        </JobInformation>
        <br />
        <h2 class="h-md">Job Parameters</h2>
        <JobParameters :job-id="id" :include-title="false" />
        <br />
        <h2 class="h-md">Job Metrics</h2>
        <JobMetrics :job-id="id" :include-title="false" />
    </b-card>
</template>

<script>
import JobMetrics from "components/JobMetrics/JobMetrics";

import JobInformation from "./JobInformation";

import CodeRow from "./CodeRow.vue";
import JobParameters from "components/JobParameters/JobParameters.vue";

export default {
    components: {
        CodeRow,
        JobInformation,
        JobMetrics,
        JobParameters,
    },
    props: {
        job: {
            type: Object,
            required: false,
        },
        jobId: {
            type: String,
            required: false,
        },
    },
    computed: {
        id() {
            return this.job?.id || this.jobId;
        },
        hasTraceback() {
            return this.job?.traceback;
        },
        hasInfo() {
            return this.job?.info;
        },
        hasRemoteHost() {
            return this.job?.remote_host;
        },
    },
};
</script>

<style scoped>
.break-word {
    white-space: pre-wrap;
    word-break: break-word;
}
</style>
