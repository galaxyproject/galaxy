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
        return `步骤 ${oneBasedStepIndex}：${props.stepLabel}`;
    }
    const workflowStepType = props.stepType;
    switch (workflowStepType) {
        case "tool":
            return `步骤 ${oneBasedStepIndex}：${toolName.value}`;
        case "subworkflow": {
            const subworkflow = subWorkflow.value;
            const label = subworkflow ? subworkflow.name : "子工作流";
            return `步骤 ${oneBasedStepIndex}：${label}`;
        }
        case "parameter_input":
            return `步骤 ${oneBasedStepIndex}：参数输入`;
        case "data_input":
            return `步骤 ${oneBasedStepIndex}：数据输入`;
        case "data_collection_input":
            return `步骤 ${oneBasedStepIndex}：数据集输入`;
        default:
            return `步骤 ${oneBasedStepIndex}：未知步骤类型 '${workflowStepType}'`;
    }
});
const hoverError = ref("");

async function initStores() {
    if (props.stepToolId && !toolStore.getToolForId(props.stepToolId)) {
        toolStore.fetchToolForId(props.stepToolId);
    }

    if (props.stepSubworkflowId) {
        try {
            await workflowStore.fetchWorkflowForInstanceId(props.stepSubworkflowId);
        } catch (e) {
            hoverError.value = errorMessageAsString(e, "获取子工作流程错误");
        }
    }
}

watch(
    props,
    async () => {
        await initStores();
    },
    { immediate: true }
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
