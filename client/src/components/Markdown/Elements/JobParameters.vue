<script setup lang="ts">
import JobParameters from "@/components/JobParameters/JobParameters.vue";

interface JobParametersProps {
    jobId: string;
    param?: string;
    title?: string;
    footer?: string;
}

withDefaults(defineProps<JobParametersProps>(), {
    param: undefined,
    title: null,
    footer: null,
});
</script>

<template>
    <b-card nobody>
        <b-card-title v-if="title">
            <b>{{ title }}</b>
        </b-card-title>
        <JobParameters class="job-parameters" :job-id="jobId" :param="param" :include-title="false" />
        <b-card-footer v-if="footer">
            {{ footer }}
        </b-card-footer>
    </b-card>
</template>
