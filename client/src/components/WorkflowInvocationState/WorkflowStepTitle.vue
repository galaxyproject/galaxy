<script setup lang="ts">
import { computed, watch } from "vue";

import { useToolStore } from "@/stores/toolStore";
import { useWorkflowStore } from "@/stores/workflowStore";

interface WorkflowInvocationStepTitleProps {
    stepIndex: number;
    stepLabel?: string;
    stepType: string;
    stepToolId?: string;
    stepSubworkflowId?: string;
}

const props = defineProps<WorkflowInvocationStepTitleProps>();

const workflowStore = useWorkflowStore();
const toolStore = useToolStore();

const subWorkflow = computed(() => {
    if (props.stepSubworkflowId) {
        return workflowStore.getStoredWorkflowByInstanceId(props.stepSubworkflowId);
    }
    return null;
});
const toolName = computed(() => {
    if (props.stepToolId) {
        return toolStore.getToolNameById(props.stepToolId);
    }
    return "";
});

const title = computed(() => {
    const oneBasedStepIndex = props.stepIndex + 1;
    if (props.stepLabel) {
        return `Step ${oneBasedStepIndex}: ${props.stepLabel}`;
    }
    const workflowStepType = props.stepType;
    switch (workflowStepType) {
        case "tool":
            return `Step ${oneBasedStepIndex}: ${toolName.value}`;
        case "subworkflow": {
            const subworkflow = subWorkflow.value;
            const label = subworkflow ? subworkflow.name : "Subworkflow";
            return `Step ${oneBasedStepIndex}: ${label}`;
        }
        case "parameter_input":
            return `Step ${oneBasedStepIndex}: Parameter input`;
        case "data_input":
            return `Step ${oneBasedStepIndex}: Data input`;
        case "data_collection_input":
            return `Step ${oneBasedStepIndex}: Data collection input`;
        default:
            return `Step ${oneBasedStepIndex}: Unknown step type '${workflowStepType}'`;
    }
});

function initStores() {
    if (props.stepToolId && !toolStore.getToolForId(props.stepToolId)) {
        toolStore.fetchToolForId(props.stepToolId);
    }

    if (props.stepSubworkflowId) {
        workflowStore.fetchWorkflowForInstanceId(props.stepSubworkflowId);
    }
}

watch(
    props,
    () => {
        initStores();
    },
    { immediate: true }
);
</script>

<template>
    <span>{{ title }}</span>
</template>
