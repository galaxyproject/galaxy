<template>
    <JobMetrics class="job-metrics" :job-id="args.job_id" />
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
