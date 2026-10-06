<script setup lang="ts">
import { faRedo, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, watch } from "vue";
import { useRoute } from "vue-router";

import type { JobBaseModel, ShowFullJobResponse } from "@/api/jobs";
import { useJobDetails } from "@/composables/jobDetails.js";
import { useToolStore } from "@/stores/toolStore";

import GButton from "../BaseComponents/GButton.vue";

const route = useRoute();

const props = defineProps<{
    jobId: string;
    /** A job object. `undefined` fetches/polls it here instead; `null` means
     * the parent confirms there's deliberately no job yet (also skips fetching). */
    job?: JobBaseModel | ShowFullJobResponse | null;
    outline?: boolean;
}>();

const fetchJobId = computed(() => (props.job === undefined ? props.jobId : undefined));
const { job: fetchedJob } = useJobDetails(fetchJobId, { full: false });
const job = computed(() => (props.job !== undefined ? props.job : fetchedJob.value));
const toolStore = useToolStore();

const rerunUrl = computed(() => `/?job_id=${props.jobId}`);

const tool = computed(() => (job.value ? toolStore.getToolForId(job.value.tool_id) : undefined));
const toolLoading = computed(() => !!job.value && !tool.value);

const canRerunJob = computed(() => !!tool.value?.is_workflow_compatible);

watch(
    () => job.value?.tool_id,
    (toolId) => {
        if (toolId && !toolStore.getToolForId(toolId)) {
            toolStore.fetchToolForId(toolId);
        }
    },
    { immediate: true },
);
</script>

<template>
    <GButton
        v-if="job"
        title="Run Job Again"
        :disabled-title="toolLoading ? 'Checking if this job can be rerun...' : 'This job cannot be rerun'"
        :disabled="toolLoading || !canRerunJob"
        size="small"
        color="blue"
        :outline="props.outline"
        :transparent="!props.outline"
        :pressed="route.fullPath === rerunUrl"
        :to="rerunUrl">
        <FontAwesomeIcon fixed-width :icon="toolLoading ? faSpinner : faRedo" :spin="toolLoading" />
        <span class="text-nowrap">Run again</span>
    </GButton>
</template>
