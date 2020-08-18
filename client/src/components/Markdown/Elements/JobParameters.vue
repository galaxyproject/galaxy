<template>
    <b-card nobody class="w-50 mx-auto">
        <JobParameters class="job-parameters" :jobId="args.job_id" :param="args.param" :includeTitle="false" />
    </b-card>
</template>

<script>
import JobParameters from "components/JobParameters/JobParameters";
export default {
    components: {
        JobParameters,
    },
    props: {
        args: {
            type: Object,
            default: null,
        },
    },
};
</script>
