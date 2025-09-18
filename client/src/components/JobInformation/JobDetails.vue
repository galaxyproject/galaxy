<template>
    <div>
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
        <Heading id="job-parameters-heading" h1 separator inline size="md"> Job Parameters </Heading>
        <JobParameters :job-id="id" :include-title="false" />
        <br />
        <Heading id="job-metrics-heading" h1 separator inline size="md"> Job Metrics </Heading>
        <JobMetrics :job-id="id" :include-title="false" />
    </div>
</template>

<script>
import JobMetrics from "components/JobMetrics/JobMetrics";

import JobInformation from "./JobInformation";

import Heading from "../Common/Heading.vue";
import CodeRow from "./CodeRow.vue";
import JobParameters from "components/JobParameters/JobParameters.vue";

export default {
    components: {
        CodeRow,
        Heading,
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
