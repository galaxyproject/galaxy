<script setup lang="ts">
import { computed, toRef, watch } from "vue";

import { useJobStore } from "@/stores/jobStore";

import { useMappingJobs } from "./handlesMappingJobs";

import JobSelection from "./JobSelection.vue";

interface ToolStdProps {
    jobId?: string;
    implicitCollectionJobsId?: string;
    name: "tool_stderr" | "tool_stdout";
}

const props = withDefaults(defineProps<ToolStdProps>(), {
    jobId: null,
    implicitCollectionJobsId: null,
});

const jobStore = useJobStore();

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

const jobContent = computed(() => {
    let content: string | undefined;
    if (targetJobId.value) {
        const job = jobStore.getJob(targetJobId.value);
        content = job && job[props.name];
    }
    if (!content && props.name == "tool_stdout") {
        content = "*No Standard Output Available*";
    } else if (!content) {
        content = "*No Standard Error Available*";
    }
    return content;
});
</script>

<template>
    <b-card nobody class="content-height">
        <JobSelection
            v-model="selectedJob"
            :job-id="jobId"
            :implicit-collection-jobs-id="implicitCollectionJobsId"
            :select-job-options="selectJobOptions">
            <div :class="name" :job_id="targetJobId">
                <pre><code class="word-wrap-normal">{{ jobContent }}</code></pre>
            </div>
        </JobSelection>
    </b-card>
</template>

<style scoped>
.content-height {
    max-height: 15rem;
    overflow-y: auto;
}
</style>
