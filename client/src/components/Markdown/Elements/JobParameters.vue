<template>
    <b-card nobody>
        <JobParameters class="job-parameters" :job-id="args.job_id" :param="args.param" :include-title="false" />
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
