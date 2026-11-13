<script setup lang="ts">
import { faExclamationTriangle, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { JobBaseModel, ShowFullJobResponse } from "@/api/jobs";
import { useJobDetails } from "@/composables/jobDetails";
import { useToolStore } from "@/stores/toolStore";
import { errorMessageAsString } from "@/utils/simple-error";

import Heading from "@/components/Common/Heading.vue";
import SuccessIconOverlay from "@/components/Common/SuccessIndicator/SuccessIconOverlay.vue";
import RerunJobButton from "@/components/JobInformation/RerunJobButton.vue";
import JobState from "@/components/JobStates/JobState.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    jobId: string;
    /** A job object. `undefined` fetches/polls it here instead; `null` means
     * the parent confirms there's deliberately no job yet (also skips fetching). */
    job?: JobBaseModel | ShowFullJobResponse | null;
    noToolName?: boolean;
    noHr?: boolean;
    animateSuccess?: boolean;
}>();

const toolStore = useToolStore();

const fetchJobId = computed(() => (props.job === undefined ? props.jobId : undefined));
const { job: fetchedJob, error } = useJobDetails(fetchJobId, { full: false });
const job = computed(() => (props.job !== undefined ? props.job : fetchedJob.value));
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
                <span v-if="job">{{ toolStore.getToolNameById(job.tool_id, "Job Details") }}</span>
                <span v-else-if="error">Job Details</span>
                <LoadingSpan v-else message="" />
            </Heading>
            <div class="job-header-end" :class="{ 'has-error': error && !job }">
                <span v-if="error && !job" class="job-header-error text-danger">
                    <FontAwesomeIcon :icon="faExclamationTriangle" fixed-width />
                    {{ errorMessageAsString(error, "Failed to load job") }}
                </span>
                <JobState v-else class="job-information-state-badge" :job-id="props.jobId" :job="job" />
                <slot name="pagination" />
                <RerunJobButton v-if="!error || job" :job-id="props.jobId" :job="job" outline />
            </div>
        </div>
        <hr v-if="!props.noHr" />
    </div>
</template>

<style lang="scss" scoped>
.job-header-title {
    min-width: 0;
    flex-shrink: 1;

    // To make it equally sized as the `covered-icon` in `SuccessIconOverlay`
    :deep(svg) {
        height: 0.85em;
    }
}

.job-header-end {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.5rem;
    flex-wrap: wrap;
    flex-shrink: 0;
    margin-left: auto;

    &.has-error {
        flex-shrink: 1;
        min-width: 0;
    }
}

.job-header-error {
    font-size: 0.875rem;
    min-width: 0;
    overflow-wrap: anywhere;
}
</style>
