<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import { useCreatingJob } from "@/composables/useCreatingJob";
import { useJobBasic } from "@/composables/useJobBasic";

import type { HistoryGraphNode } from "./historyGraphMapper";

import JobDetailsTabs from "./JobDetailsTabs.vue";
import ToolExecutionJobs from "./ToolExecutionJobs.vue";
import GTabs from "@/components/BaseComponents/GTabs.vue";
import RerunJobButton from "@/components/JobInformation/RerunJobButton.vue";
import JobState from "@/components/JobStates/JobState.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    /** The graph node to render details for. */
    node: HistoryGraphNode;
}

const props = defineProps<Props>();

const nodeSrc = computed(() => props.node.data?.src ?? null);
const itemId = computed(() => props.node.data?.itemId ?? null);
const isDatasetLike = computed(() => nodeSrc.value === "hda" || nodeSrc.value === "hdca");

// Labels for the Information tab now that the BCard header is gone.
const infoTitle = computed(() => (props.node?.label as string) ?? undefined);
const infoIcon = computed(() => props.node?.icon);

// For dataset/collection nodes, resolve the creating job and fetch its basic
// details for the JobState badge / RerunJobButton in the GTabs nav-end.
const { jobId: creatingJobId, loading: lookupLoading, error: lookupError } = useCreatingJob(itemId, nodeSrc);
const { job } = useJobBasic(creatingJobId);
</script>

<template>
    <ToolExecutionJobs
        v-if="nodeSrc === 'tool_request' && itemId"
        :tool-execution-id="itemId"
        :info-title="infoTitle"
        :info-icon="infoIcon" />
    <div v-else>
        <LoadingSpan v-if="isDatasetLike && lookupLoading" message="Loading job details" />
        <BAlert v-else-if="isDatasetLike && lookupError" variant="info" show class="mb-0">{{ lookupError }}</BAlert>
        <GTabs v-else-if="isDatasetLike && creatingJobId">
            <template v-slot:nav-end>
                <JobState v-if="job" :job="job" class="mr-2" />
                <RerunJobButton v-if="job" :job-id="creatingJobId" outline />
            </template>
            <JobDetailsTabs
                :key="creatingJobId"
                :job-id="creatingJobId"
                :info-title="infoTitle"
                :info-icon="infoIcon" />
        </GTabs>
        <BAlert v-else show variant="info" class="mb-0">No details available for this node.</BAlert>
    </div>
</template>
