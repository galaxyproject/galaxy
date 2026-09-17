<script setup lang="ts">
import { faWrench } from "@fortawesome/free-solid-svg-icons";
import { toRef } from "vue";

import { useJobDetails } from "@/composables/jobDetails";
import { useToolStore } from "@/stores/toolStore";

import Heading from "@/components/Common/Heading.vue";
import RerunJobButton from "@/components/JobInformation/RerunJobButton.vue";
import JobState from "@/components/JobStates/JobState.vue";

const props = defineProps<{
    jobId: string;
}>();

const toolStore = useToolStore();

const { job } = useJobDetails(toRef(props, "jobId"));
</script>

<template>
    <div>
        <div class="d-flex justify-content-between">
            <Heading v-if="job" :icon="faWrench" inline size="md">
                {{ toolStore.getToolNameById(job.tool_id, "Job Details") }}
            </Heading>
            <div class="job-header-end">
                <JobState class="job-information-state-badge" :job-id="props.jobId" />
                <slot name="pagination" />
                <RerunJobButton :job-id="props.jobId" outline />
            </div>
        </div>
        <hr v-if="job" />
    </div>
</template>

<style lang="scss" scoped>
.job-header-end {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.5rem;
    flex-wrap: wrap;
}
</style>
