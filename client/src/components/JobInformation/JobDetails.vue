<template>
    <b-card>
        <job-information :job_id="id" :include-times="true">
            <tr v-if="hasTraceback">
                <td>Traceback</td>
                <td>
                    <code-row :code-label="'Traceback'" :code-item="job.traceback" />
                </td>
            </tr>
            <tr v-if="hasInfo">
                <td>Info</td>
                <td>
                    <code-row :code-label="'Info'" :code-item="job.info" />
                </td>
            </tr>
            <tr v-if="hasRemoteHost">
                <td>Remote Host</td>
                <td>
                    {{ job.remote_host }}
                </td>
            </tr>
        </job-information>
        <br />
        <h3>Job Parameters</h3>
        <job-parameters :job-id="id" :include-title="false" />
        <br />
        <h3>Job Metrics</h3>
        <job-metrics :job-id="id" :include-title="false" />
    </b-card>
</template>

<script>
import JobMetrics from "components/JobMetrics/JobMetrics";
import JobParameters from "components/JobParameters/JobParameters.vue";
import JobInformation from "./JobInformation";
import CodeRow from "./CodeRow.vue";

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
