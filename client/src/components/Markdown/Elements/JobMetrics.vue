<template>
    <JobMetrics class="job-metrics" :jobId="args.job_id" />
</template>

<script>
import JobMetrics from "components/JobMetrics/JobMetrics";
export default {
    components: {
        JobMetrics,
    },
    props: {
        args: {
            type: Object,
            default: null,
        },
    },
};
</script>
