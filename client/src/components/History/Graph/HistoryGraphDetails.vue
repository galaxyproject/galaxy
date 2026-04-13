<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { GraphNode } from "@/components/Graph/types";

import Heading from "@/components/Common/Heading.vue";
import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";
import JobInformation from "@/components/JobInformation/JobInformation.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    node: GraphNode;
}

const props = defineProps<Props>();

const nodeType = computed(() => (props.node?.data?.type as string) ?? null);
const encodedId = computed(() => (props.node?.data?.encodedId as string) ?? null);

/** Map graph node type to the item source GenericHistoryItem expects */
const itemSrc = computed(() => {
    if (nodeType.value === "dataset") {
        return "hda";
    }
    if (nodeType.value === "collection") {
        return "hdca";
    }
    return null;
});

// Tool request -> job ID resolution
const jobId = ref<string | null>(null);
const jobLoading = ref(false);
const jobError = ref<string | null>(null);

watch(
    () => [nodeType.value, encodedId.value],
    async ([type, id]) => {
        jobId.value = null;
        jobError.value = null;
        if (type !== "tool_request" || !id) {
            return;
        }
        jobLoading.value = true;
        try {
            const { data, error } = await GalaxyApi().GET("/api/tool_requests/{id}", {
                params: { path: { id: id as string } },
            });
            if (error) {
                jobError.value = "Failed to load tool request details.";
            } else if (data.jobs && data.jobs.length > 0) {
                jobId.value = data.jobs[0]!.id;
            } else {
                jobError.value = "No job associated with this tool execution.";
            }
        } catch (e) {
            jobError.value = "Failed to load tool request details.";
        } finally {
            jobLoading.value = false;
        }
    },
    { immediate: true },
);
</script>

<template>
    <div class="history-graph-details border-left bg-white">
        <div class="details-body">
            <!-- Dataset or Collection -->
            <div v-if="itemSrc && encodedId" :key="encodedId" class="p-2">
                <Heading h1 separator inline size="md">
                    {{ nodeType === "dataset" ? "Dataset Information" : "Collection Information" }}
                </Heading>
                <GenericHistoryItem :item-id="encodedId" :item-src="itemSrc" />
            </div>

            <!-- Tool request / Job details -->
            <div v-else-if="nodeType === 'tool_request'" class="p-2">
                <LoadingSpan v-if="jobLoading" message="Loading job details" />
                <BAlert v-else-if="jobError" variant="info" show class="mb-0">{{ jobError }}</BAlert>
                <JobInformation v-else-if="jobId" :job-id="jobId" :include-times="true" />
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.history-graph-details {
    flex-shrink: 0;
    width: 320px;
    height: 100%;
    overflow-y: auto;
}
</style>
