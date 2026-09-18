<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { BAlert, BPagination } from "bootstrap-vue";
import { computed, ref, toRef } from "vue";

import { useToolExecutionJobs } from "./useToolExecutionJobs";

import JobDetailsTabs from "./JobDetailsTabs.vue";
import GTabs from "@/components/BaseComponents/GTabs.vue";
import JobHeader from "@/components/JobInformation/JobHeader.vue";
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
                    <JobHeader v-if="currentJob" :job-id="currentJob.id" no-tool-name>
                        <template v-slot:pagination>
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
                        </template>
                    </JobHeader>
                </template>
                <JobDetailsTabs :job-id="currentJob.id" :info-title="props.infoTitle" :info-icon="props.infoIcon" />
            </GTabs>
        </template>
    </div>
</template>
