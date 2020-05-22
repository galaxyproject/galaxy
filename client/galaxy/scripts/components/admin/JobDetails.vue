<template>
    <b-card>
        <h5>Command Line</h5>
        <pre class="text-white bg-dark"><code class="break-word">{{ commandLine }}</code></pre>
        <h5>Job Parameters</h5>
        <job-parameters :job-id="jobId" :include-title="false" />
        <h5>Job Metrics</h5>
        <job-metrics :job-id="jobId" :include-title="false" />
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
        commandLine: {
            type: String,
            required: true,
        },
        jobId: {
            type: String,
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
