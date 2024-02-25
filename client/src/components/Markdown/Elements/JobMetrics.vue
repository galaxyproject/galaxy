<template>
    <b-card nobody>
        <JobMetrics
            class="job-metrics"
            :job-id="args.job_id"
            :should-show-aws-estimate="false"
            :should-show-carbon-emission-estimates="false"
            :include-title="false" />
    </b-card>
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
