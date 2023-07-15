<template>
    <GCard nobody>
        <JobParameters class="job-parameters" :job-id="args.job_id" :param="args.param" :include-title="false" />
    </GCard>
</template>

<script>
import JobParameters from "components/JobParameters/JobParameters";

import GCard from "@/component-library/GCard.vue";

export default {
    components: {
        GCard,
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
