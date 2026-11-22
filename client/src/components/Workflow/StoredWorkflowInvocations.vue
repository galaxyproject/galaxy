<script setup lang="ts">
import { onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { rethrowSimple } from "@/utils/simple-error";

import LoadingSpan from "../LoadingSpan.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import Heading from "@/components/Common/Heading.vue";
import InvocationList from "@/components/Workflow/Invocation/InvocationList.vue";

interface Props {
    storedWorkflowId: string;
}
const props = defineProps<Props>();

const loading = ref(true);
const workflow = ref<StoredWorkflowDetailed>();

onMounted(async () => {
    try {
        const { data, error } = await GalaxyApi().GET("/api/workflows/{workflow_id}", {
            params: { path: { workflow_id: props.storedWorkflowId } },
        });

        if (error) {
            rethrowSimple(error);
        }

        workflow.value = data;
    } finally {
        loading.value = false;
    }
});
</script>

<template>
    <div v-if="!loading && workflow" class="d-flex flex-column h-100">
        <Heading h1 separator inline truncate size="lg" class="mb-2">
            Workflow Invocations for Workflow "{{ workflow.name }}"
        </Heading>
        <InvocationList
            :workflow-id="workflow.id"
            :no-data-message="`No Workflow Invocations to display for ${workflow.name}`" />
    </div>
    <GAlert v-else-if="loading" variant="info" show>
        <LoadingSpan message="Loading invocations for workflow" />
    </GAlert>
    <GAlert v-else variant="danger" show>
        <p>Failed to load stored workflow with ID: {{ props.storedWorkflowId }}</p>
    </GAlert>
</template>
