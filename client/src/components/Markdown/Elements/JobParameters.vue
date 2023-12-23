<script setup lang="ts">
import { computed, watch } from "vue";

import { useJobStore } from "@/stores/jobStore";

import JobParameters from "@/components/JobParameters/JobParameters.vue";
import ToolLinkPopover from "@/components/Tool/ToolLinkPopover.vue";

interface JobParametersProps {
    jobId: string;
    param?: string;
    title?: string;
    footer?: string;
}

const props = withDefaults(defineProps<JobParametersProps>(), {
    param: undefined,
    title: undefined,
    footer: undefined,
});

const jobStore = useJobStore();

const toolId = computed(() => {
    return jobStore.getJob(props.jobId)?.tool_id;
});
const toolVersion = computed(() => {
    return jobStore.getJob(props.jobId)?.tool_version;
});

watch(
    props,
    () => {
        jobStore.fetchJob(props.jobId);
    },
    { immediate: true }
);
</script>

<template>
    <b-card nobody>
        <b-card-title v-if="title">
            <b>{{ title }}</b>
            <icon ref="info" icon="info-circle" size="sm" />
            <ToolLinkPopover :target="() => $refs.info" :tool-id="toolId" :tool-version="toolVersion" />
        </b-card-title>
        <JobParameters class="job-parameters" :job-id="jobId" :param="param" :include-title="false" />
        <b-card-footer v-if="footer">
            {{ footer }}
        </b-card-footer>
    </b-card>
</template>
