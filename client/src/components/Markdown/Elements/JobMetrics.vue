<script setup lang="ts">
import { computed, toRef, watch } from "vue";

import { useJobStore } from "@/stores/jobStore";

import { useMappingJobs } from "./handlesMappingJobs";

import JobSelection from "./JobSelection.vue";
import JobMetrics from "@/components/JobMetrics/JobMetrics.vue";
import ToolLinkPopover from "@/components/Tool/ToolLinkPopover.vue";

interface JobMetricsProps {
    jobId?: string;
    implicitCollectionJobsId?: string;
    title?: string;
    footer?: string;
}

const props = withDefaults(defineProps<JobMetricsProps>(), {
    jobId: undefined,
    implicitCollectionJobsId: undefined,
    title: undefined,
    footer: undefined,
});

const jobStore = useJobStore();

const toolId = computed(() => {
    if (targetJobId.value) {
        return jobStore.getJob(targetJobId.value)?.tool_id;
    }
    return undefined;
});
const toolVersion = computed(() => {
    if (targetJobId.value) {
        return jobStore.getJob(targetJobId.value)?.tool_version;
    }
    return undefined;
});
const jobIdRef = toRef(props, "jobId");
const implicitCollectionJobsIdRef = toRef(props, "implicitCollectionJobsId");

const { selectJobOptions, selectedJob, targetJobId } = useMappingJobs(jobIdRef, implicitCollectionJobsIdRef);

async function init() {
    if (targetJobId.value) {
        jobStore.fetchJob(targetJobId.value);
    }
}

watch(
    targetJobId,
    () => {
        init();
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
        <JobSelection
            v-model="selectedJob"
            :job-id="jobId"
            :implicit-collection-jobs-id="implicitCollectionJobsId"
            :select-job-options="selectJobOptions">
            <JobMetrics
                v-if="targetJobId"
                class="job-metrics"
                :job-id="targetJobId"
                :should-show-aws-estimate="false"
                :should-show-carbon-emission-estimates="false"
                :include-title="false" />
        </JobSelection>
        <b-card-footer v-if="footer">
            {{ footer }}
        </b-card-footer>
    </b-card>
</template>
