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
            <div class="job-header">
                <div class="job-header-title">
                    <JobState v-if="job" class="job-information-state-badge" :job="job" />
                    <Heading v-if="job" :icon="faWrench" inline size="md">
                        {{ toolStore.getToolNameById(job.tool_id, "Job Details") }}
                    </Heading>
                </div>
                <slot name="details" />
            </div>
            <div>
                <RerunJobButton :job-id="props.jobId" outline />
            </div>
        </div>
        <hr />
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
