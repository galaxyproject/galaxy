<template>
    <div class="w-100 p-2">
        <b-card nobody>
            <JobMetrics class="job-metrics" :job-id="args.job_id" />
        </b-card>
    </div>
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
