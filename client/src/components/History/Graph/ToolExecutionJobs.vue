<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { BAlert, BPagination } from "bootstrap-vue";
import { computed, ref, toRef } from "vue";

import { useJobBasic } from "@/composables/useJobBasic";

import { useToolExecutionJobs } from "./useToolExecutionJobs";

import JobDetailsTabs from "./JobDetailsTabs.vue";
import GTabs from "@/components/BaseComponents/GTabs.vue";
import RerunJobButton from "@/components/JobInformation/RerunJobButton.vue";
import JobState from "@/components/JobStates/JobState.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    /** Encoded tool-execution (tool_request) id whose jobs should be listed. */
    toolExecutionId: string;
    /** Custom text for the Information tab title (forwarded to JobDetailsTabs). */
    infoTitle?: string;
    /** Custom icon for the Information tab title (forwarded to JobDetailsTabs). */
    infoIcon?: IconDefinition;
}

const props = defineProps<Props>();

const { jobs, loading, error } = useToolExecutionJobs(toRef(props, "toolExecutionId"));

const currentIndex = ref(0);
const currentJob = computed(() => jobs.value[currentIndex.value] ?? null);

// Job details for the state badge in the tab nav-end, via the shared
// jobStore cache. The Information / Parameters / Outputs tabs each fetch
// their own data internally via JobDetailsTabs.
const { job } = useJobBasic(computed(() => currentJob.value?.id ?? null));

const hasMany = computed(() => jobs.value.length > 1);

// BPagination is 1-indexed; bridge to the 0-indexed currentIndex.
const paginationPage = computed<number>({
    get: () => currentIndex.value + 1,
    set: (val: number) => {
        currentIndex.value = val - 1;
    },
});
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" message="Loading job details" />
        <BAlert v-else-if="error" variant="info" show class="mb-0">{{ error }}</BAlert>
        <template v-else-if="currentJob">
            <GTabs>
                <template v-slot:nav-end>
                    <JobState v-if="job" :job="job" class="mr-2" />
                    <BPagination
                        v-if="hasMany"
                        v-model="paginationPage"
                        :total-rows="jobs.length"
                        :per-page="1"
                        size="sm"
                        :limit="3"
                        first-number
                        last-number
                        hide-goto-end-buttons
                        class="mb-0 mr-2" />
                    <RerunJobButton v-if="job" :job-id="currentJob.id" outline />
                </template>
                <JobDetailsTabs :job-id="currentJob.id" :info-title="props.infoTitle" :info-icon="props.infoIcon" />
            </GTabs>
        </template>
    </div>
</template>
