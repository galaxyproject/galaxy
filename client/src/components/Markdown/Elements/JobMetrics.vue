<script setup lang="ts">
import JobMetrics from "@/components/JobMetrics/JobMetrics.vue";

interface JobMetricsProps {
    jobId: string;
    title?: string;
    footer?: string;
}

withDefaults(defineProps<JobMetricsProps>(), {
    title: null,
    footer: null,
});
</script>

<template>
    <b-card nobody>
        <b-card-title v-if="title">
            <b>{{ title }}</b>
        </b-card-title>
        <JobMetrics
            class="job-metrics"
            :job-id="jobId"
            :should-show-aws-estimate="false"
            :should-show-carbon-emissions-estimates="false"
            :include-title="false" />
        <b-card-footer v-if="footer">
            {{ footer }}
        </b-card-footer>
    </b-card>
</template>
