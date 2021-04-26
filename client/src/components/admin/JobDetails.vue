<template>
    <b-card>
        <job-information :job_id="job.id" :includeTimes="true">
            <tr v-if="job.traceback">
                <td>Traceback</td>
                <td>
                    <code-row :code-label="'Traceback'" :code-item="job.traceback" />
                </td>
            </tr>
            <tr v-if="job.info">
                <td>Info</td>
                <td>
                    <code-row :code-label="'Traceback'" :code-item="job.traceback" />
                </td>
            </tr>
            <tr v-if="job.remote_host">
                <td>Remote Host</td>
                <td>
                    {{ job.remote_host }}
                </td>
            </tr>
        </job-information>
        <br />
        <h3>Job Parameters</h3>
        <job-parameters :job-id="job.id" :include-title="false" />
        <br />
        <h3>Job Metrics</h3>
        <job-metrics :job-id="job.id" :include-title="false" />
    </b-card>
</template>

<script>
import { JobMetrics } from "components/JobMetrics";
import { JobParameters } from "components/JobParameters";
import JobInformation from "components/JobInformation/JobInformation";
import CodeRow from "components/JobInformation/CodeRow.vue";

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
            required: true,
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
