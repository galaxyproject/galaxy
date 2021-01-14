<template>
    <b-card>
        <h5>Job Parameters</h5>
        <job-parameters :job-id="job.id" :include-title="false" />
        <h5>Job Metrics</h5>
        <job-metrics :job-id="job.id" :include-title="false" />
    </b-card>
</template>

<script>
import { JobMetrics } from "components/JobMetrics";
import { JobParameters } from "components/JobParameters";

export default {
    components: {
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
