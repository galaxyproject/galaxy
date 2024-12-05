<script setup lang="ts">
import { BAlert, BCard } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { ref } from "vue";

import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { errorMessageAsString } from "@/utils/simple-error";

import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

interface Props {
    workflowId: string;
    storedId: string;
    version: number;
}

const props = defineProps<Props>();

const { workflow } = useWorkflowInstance(props.storedId);

const { datatypesMapper } = useDatatypesMapper();

const loadingWorkflow = ref(true);
const errorLoadingWorkflow = ref<string | null>(null);
const loadedWorkflow = ref<any | null>(null);

const { activeNodeId } = storeToRefs(useWorkflowStateStore(props.workflowId));

loadWorkflow();

async function loadWorkflow() {
    try {
        loadedWorkflow.value = await getWorkflowFull(props.workflowId, props.version);
    } catch (error) {
        errorLoadingWorkflow.value = errorMessageAsString(error);
    } finally {
        loadingWorkflow.value = false;
    }
}

function toggleActiveStep(stepId: number) {
    if (activeNodeId.value === stepId) {
        activeNodeId.value = null;
    } else {
        activeNodeId.value = stepId;
    }
}
</script>

<template>
    <BAlert v-if="loadingWorkflow" variant="info" show>
        <LoadingSpan message="Loading workflow" />
    </BAlert>
    <BAlert v-else-if="errorLoadingWorkflow" variant="danger" show>
        {{ errorLoadingWorkflow }}
    </BAlert>
    <div v-else-if="workflow && loadedWorkflow && datatypesMapper">
        <Heading size="md" separator>Description</Heading>
        <BCard class="workflow-preview">
            <WorkflowGraph
                :steps="loadedWorkflow.steps"
                :datatypes-mapper="datatypesMapper"
                fixed-height
                show-minimap
                show-zoom-controls
                readonly />
        </BCard>
    </div>
</template>
