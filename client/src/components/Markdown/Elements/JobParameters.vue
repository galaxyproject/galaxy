<template>
    <div class="w-50 p-2 float-left">
        <b-card nobody>
            <JobParameters class="job-parameters" :job-id="args.job_id" :param="args.param" :include-title="false" />
        </b-card>
    </div>
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
