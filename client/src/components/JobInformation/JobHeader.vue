<script setup lang="ts">
import { faWrench } from "@fortawesome/free-solid-svg-icons";

import type { ShowFullJobResponse } from "@/api/jobs";
import { useToolStore } from "@/stores/toolStore";

import Heading from "@/components/Common/Heading.vue";
import RerunJobButton from "@/components/JobInformation/RerunJobButton.vue";
import JobState from "@/components/JobStates/JobState.vue";

const props = defineProps<{
    job: ShowFullJobResponse;
}>();

const toolStore = useToolStore();
</script>

<template>
    <div class="d-flex justify-content-between">
        <div class="job-header">
            <div class="job-header-title">
                <JobState v-if="props.job" class="job-information-state-badge" :job="props.job" />
                <Heading v-if="props.job" :icon="faWrench" inline size="md">
                    {{ toolStore.getToolNameById(props.job.tool_id, "Job Details") }}
                </Heading>
            </div>
            <slot name="details" />
        </div>
        <div v-if="props.job">
            <RerunJobButton :job-id="props.job.id" outline />
        </div>
    </div>
</template>

<style lang="scss" scoped>
.job-header {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.job-header-title {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    flex-wrap: wrap;
}
</style>
