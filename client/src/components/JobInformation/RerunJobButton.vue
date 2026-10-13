<script setup lang="ts">
import { faRedo, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRoute } from "vue-router";

import type { JobBaseModel, ShowFullJobResponse } from "@/api/jobs";
import { useJobDetails } from "@/composables/jobDetails.js";
import { useRerunnableTool } from "@/composables/rerunnableTool";

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

const rerunUrl = computed(() => `/?job_id=${props.jobId}`);

const {
    canRerun: canRerunJob,
    loading: toolLoading,
    error: toolError,
} = useRerunnableTool(computed(() => job.value?.tool_id));

const disabledTitle = computed(() => {
    if (toolLoading.value) {
        return "Checking if this job can be rerun...";
    }
    if (toolError.value) {
        return `Could not check if this job can be rerun: ${toolError.value}`;
    }
    return "This job cannot be rerun";
});
</script>

<template>
    <GButton
        v-if="job"
        title="Run Job Again"
        :disabled-title="disabledTitle"
        :disabled="toolLoading || !canRerunJob"
        size="small"
        color="blue"
        :outline="props.outline"
        :transparent="!props.outline"
        :pressed="route.fullPath === rerunUrl"
        :to="rerunUrl">
        <!-- Separate icons rather than a dynamic `icon` prop: an in-place patch of `FontAwesomeIcon`'s
            icon doesn't always re-render, leaving the spinner after the check settles while disabled. -->
        <FontAwesomeIcon v-if="toolLoading" fixed-width :icon="faSpinner" spin />
        <FontAwesomeIcon v-else fixed-width :icon="faRedo" />
        <span class="text-nowrap">Run again</span>
    </GButton>
</template>
