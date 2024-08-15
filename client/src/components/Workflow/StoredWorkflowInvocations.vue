<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { onMounted, ref } from "vue";

import { type StoredWorkflowDetailed, workflowFetcher } from "@/api/workflows";

import GridInvocation from "../Grid/GridInvocation.vue";
import LoadingSpan from "../LoadingSpan.vue";

interface Props {
    storedWorkflowId: string;
}
const props = defineProps<Props>();

const loading = ref(true);
const workflow = ref<StoredWorkflowDetailed | undefined>(undefined);

onMounted(async () => {
    try {
        const { data } = await workflowFetcher({ workflow_id: props.storedWorkflowId });
        workflow.value = data;
    } catch (error) {
        console.error(error);
    } finally {
        loading.value = false;
    }
});
</script>

<template>
    <GridInvocation
        v-if="!loading && workflow"
        :filtered-for="{
            type: 'StoredWorkflow',
            id: workflow.id,
            name: workflow.name,
        }" />
    <BAlert v-else-if="loading" variant="info" show>
        <LoadingSpan message="Loading invocations for workflow" />
    </BAlert>
    <BAlert v-else variant="danger" show>
        <p>Failed to load stored workflow with ID: {{ props.storedWorkflowId }}</p>
    </BAlert>
</template>
