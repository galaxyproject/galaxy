<script setup lang="ts">
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import { useToolStore } from "@/stores/toolStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { errorMessageAsString } from "@/utils/simple-error";

interface WorkflowInvocationStepTitleProps {
    stepIndex: number;
    stepLabel?: string;
    stepType: string;
    stepToolId?: string | null;
    stepToolUuid?: string | null;
    stepSubworkflowId?: string | null;
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
    const toolId = props.stepToolUuid || props.stepToolId;
    if (toolId) {
        return toolStore.getToolNameById(toolId);
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
const hoverError = ref("");

async function initStores() {
    const toolId = props.stepToolUuid || props.stepToolId;
    if (toolId && !toolStore.getToolForId(toolId)) {
        toolStore.fetchToolForId(toolId);
    }

    if (props.stepSubworkflowId) {
        try {
            await workflowStore.fetchWorkflowForInstanceId(props.stepSubworkflowId);
        } catch (e) {
            hoverError.value = errorMessageAsString(e, "Error fetching subworkflow");
        }
    }
}

watch(
    props,
    async () => {
        await initStores();
    },
    { immediate: true },
);
</script>

<template>
    <span>
        {{ title }}
        <span v-b-tooltip.noninteractive.hover.v-danger :title="hoverError">
            <FontAwesomeIcon v-if="hoverError" class="text-danger" :icon="faExclamationCircle" />
        </span>
    </span>
</template>
