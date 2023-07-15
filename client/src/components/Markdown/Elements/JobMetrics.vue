<template>
    <GCard nobody>
        <JobMetrics class="job-metrics" :job-id="args.job_id" />
    </GCard>
</template>

<script>
import JobMetrics from "components/JobMetrics/JobMetrics";

import GCard from "@/component-library/GCard.vue";

export default {
    components: {
        GCard,
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
