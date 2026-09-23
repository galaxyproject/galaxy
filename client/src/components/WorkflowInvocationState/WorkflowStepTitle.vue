<script setup lang="ts">
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import type { InvocationStep } from "@/api/invocations";
import type { WorkflowStepTyped } from "@/api/workflows";
import { getStepTitle } from "@/components/WorkflowInvocationState/util";
import { useToolStore } from "@/stores/toolStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { errorMessageAsString } from "@/utils/simple-error";

interface WorkflowInvocationStepTitleProps {
    workflowStep: WorkflowStepTyped;
    invocationStep?: InvocationStep;
}

const props = defineProps<WorkflowInvocationStepTitleProps>();

const workflowStore = useWorkflowStore();
const toolStore = useToolStore();

const stepSubworkflowId = computed(() => ("workflow_id" in props.workflowStep ? props.workflowStep.workflow_id : null));
const toolId = computed(() => props.workflowStep.tool_uuid || props.workflowStep.tool_id);

const title = computed(() => {
    const toolName = toolId.value ? toolStore.getToolNameById(toolId.value) : undefined;
    const subworkflowName = stepSubworkflowId.value
        ? workflowStore.getStoredWorkflowByInstanceId(stepSubworkflowId.value)?.name
        : undefined;
    return getStepTitle(
        props.workflowStep.id,
        props.workflowStep.type,
        props.invocationStep?.workflow_step_label || undefined,
        toolName || undefined,
        subworkflowName,
    );
});

const hoverError = ref("");

async function initStores() {
    if (toolId.value && !toolStore.getToolForId(toolId.value)) {
        toolStore.fetchToolForId(toolId.value);
    }

    if (stepSubworkflowId.value) {
        try {
            await workflowStore.fetchWorkflowForInstanceId(stepSubworkflowId.value);
        } catch (e) {
            hoverError.value = errorMessageAsString(e, "Error fetching subworkflow");
        }
    }
}

watch(
    () => [props.workflowStep, props.invocationStep],
    async () => {
        await initStores();
    },
    { immediate: true },
);
</script>

<template>
    <span>
        {{ title }}
        <span v-g-tooltip.hover.v-danger :title="hoverError">
            <FontAwesomeIcon v-if="hoverError" class="text-danger" :icon="faExclamationCircle" />
        </span>
    </span>
</template>
