<script setup lang="ts">
import { faWrench } from "@fortawesome/free-solid-svg-icons";
import { toRef } from "vue";

import { useJobDetails } from "@/composables/jobDetails";
import { useToolStore } from "@/stores/toolStore";

import Heading from "@/components/Common/Heading.vue";
import SuccessIconOverlay from "@/components/Common/SuccessIndicator/SuccessIconOverlay.vue";
import RerunJobButton from "@/components/JobInformation/RerunJobButton.vue";
import JobState from "@/components/JobStates/JobState.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    jobId: string;
    noToolName?: boolean;
    animateSuccess?: boolean;
}>();

const toolStore = useToolStore();

const { job } = useJobDetails(toRef(props, "jobId"));
</script>

<template>
    <div>
        <div class="d-flex justify-content-between">
            <Heading
                v-if="!props.noToolName"
                class="job-header-title"
                :icon="!props.animateSuccess ? faWrench : undefined"
                inline
                size="md">
                <SuccessIconOverlay v-if="props.animateSuccess" :covered-icon="faWrench" />
                <LoadingSpan v-if="!job" message="" />
                <span v-else>{{ toolStore.getToolNameById(job.tool_id, "Job Details") }}</span>
            </Heading>
            <div class="job-header-end">
                <JobState class="job-information-state-badge" :job-id="props.jobId" />
                <slot name="pagination" />
                <RerunJobButton :job-id="props.jobId" outline />
            </div>
        </div>
        <hr />
    </div>
</template>

<style lang="scss" scoped>
.job-header-title {
    min-width: 0;
    flex-shrink: 1;
}

.job-header-end {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.5rem;
    flex-wrap: wrap;
    flex-shrink: 0;
    margin-left: auto;
}
</style>
