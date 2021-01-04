<template>
    <div class="w-50 p-2 float-left">
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
