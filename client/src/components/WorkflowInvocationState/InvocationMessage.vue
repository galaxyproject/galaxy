<script setup lang="ts">
import { computed } from "vue";

import type { InvocationMessage, WorkflowInvocationElementView } from "@/api/invocations";
import { useInvocationMessageStepData } from "@/composables/useInvocationMessageStepData";

import { INVOCATION_MSG_LEVEL } from "./util";

const LEVEL_CLASSES = {
    warning: "warningmessage",
    cancel: "infomessage",
    error: "errormessage",
};

const CANCEL_FRAGMENT = "Invocation scheduling cancelled because";
const FAIL_FRAGMENT = "Invocation scheduling failed because ";

interface Props {
    invocationMessage: InvocationMessage;
    invocation?: WorkflowInvocationElementView;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "view-step", stepId: number): void;
    (e: "view-subworkflow-invocation", invocationId: string, stepId: number): void;
}>();

// Create stable computed refs for the composable to avoid re-fetching on every render
const invocationId = computed(() => props.invocation?.id || "");
const pathStepOrderIndices = computed(() => {
    if (
        "workflow_step_id_path" in props.invocationMessage &&
        Array.isArray(props.invocationMessage.workflow_step_id_path)
    ) {
        return props.invocationMessage.workflow_step_id_path as number[];
    }
    return [];
});
const finalStepOrderIndex = computed(() => {
    if ("workflow_step_id" in props.invocationMessage) {
        return props.invocationMessage.workflow_step_id as number;
    }
    return undefined;
});

// Use the composable to fetch enriched step data with proper labels for nested subworkflows
const { stepData, loading, error } = useInvocationMessageStepData(
    invocationId,
    pathStepOrderIndices,
    finalStepOrderIndex,
);

// Check if we have step path information and can make it clickable
const hasClickableStepPath = computed(() => {
    return props.invocation && stepData.value.length > 0 && !loading.value && !error.value;
});

// Build array of step info for rendering clickable badges from the enriched step data
const stepPathInfo = computed(() => {
    return stepData.value.map((step) => ({
        workflowStepId: step.workflowStepId,
        invocationStepId: step.invocationStepId,
        subworkflowInvocationId: step.subworkflowInvocationId,
        label: step.label,
        type: step.stepType,
        isSubworkflow: step.stepType === "subworkflow",
        isFinalStep: step.isFinalStep,
        parentInvocationId: step.parentInvocationId,
    }));
});

function buildStepPath(message: InvocationMessage): string {
    if (
        "workflow_step_id_path" in message &&
        "workflow_step_id" in message &&
        message.workflow_step_id_path &&
        Array.isArray(message.workflow_step_id_path) &&
        message.workflow_step_id_path.length > 0 &&
        message.workflow_step_id !== null &&
        message.workflow_step_id !== undefined
    ) {
        // Build path like "Step 2 → Step 5 → Step 9"
        const pathSteps = (message.workflow_step_id_path as number[]).map((id: number) => `Step ${id + 1}`).join(" → ");
        return `${pathSteps} → Step ${message.workflow_step_id + 1}`;
    }
    if ("workflow_step_id" in message && message.workflow_step_id !== null && message.workflow_step_id !== undefined) {
        return `step ${message.workflow_step_id + 1}`;
    }
    return "";
}

function handleStepClick(stepInfo: any) {
    // If this step has a parentInvocationId, it's in a subworkflow
    if (stepInfo.parentInvocationId) {
        // Navigate to the parent (subworkflow) invocation and highlight this step
        emit("view-subworkflow-invocation", stepInfo.parentInvocationId, stepInfo.workflowStepId);
    }
    // If this is the final step in a subworkflow, navigate to that subworkflow invocation
    else if (stepInfo.isFinalStep && stepInfo.subworkflowInvocationId) {
        emit("view-subworkflow-invocation", stepInfo.subworkflowInvocationId, stepInfo.workflowStepId);
    }
    // If this is a subworkflow step in the path, navigate to that subworkflow invocation
    else if (stepInfo.isSubworkflow && stepInfo.subworkflowInvocationId) {
        emit("view-subworkflow-invocation", stepInfo.subworkflowInvocationId, 0);
    }
    // Otherwise, navigate to the step in the current workflow
    else {
        emit("view-step", stepInfo.workflowStepId);
    }
}

const levelClass = computed(() => LEVEL_CLASSES[INVOCATION_MSG_LEVEL[props.invocationMessage.reason]]);

// Compute message parts for rendering with clickable steps
const messageInfo = computed(() => {
    const invocationMessage = props.invocationMessage;
    const reason = invocationMessage.reason;

    if (reason === "user_request") {
        return { text: `${CANCEL_FRAGMENT} user requested cancellation.`, hasStepPath: false };
    } else if (reason === "history_deleted") {
        return { text: `${CANCEL_FRAGMENT} the history of the invocation was deleted.`, hasStepPath: false };
    } else if (reason === "cancelled_on_review") {
        return {
            text: `${CANCEL_FRAGMENT} the invocation was paused at step ${
                invocationMessage.workflow_step_id + 1
            } and not approved.`,
            hasStepPath: false,
        };
    } else if (reason === "collection_failed") {
        return {
            text: `${FAIL_FRAGMENT} step ${
                invocationMessage.workflow_step_id + 1
            } requires a dataset collection created by step ${
                invocationMessage.dependent_workflow_step_id + 1
            }, but dataset collection entered a failed state.`,
            hasStepPath: false,
        };
    } else if (reason === "dataset_failed") {
        if (
            invocationMessage.dependent_workflow_step_id !== null &&
            invocationMessage.dependent_workflow_step_id !== undefined
        ) {
            return {
                text: `${FAIL_FRAGMENT} step ${
                    invocationMessage.workflow_step_id + 1
                } requires a dataset created by step ${
                    invocationMessage.dependent_workflow_step_id + 1
                }, but dataset entered a failed state.`,
                hasStepPath: false,
            };
        } else {
            return {
                text: `${FAIL_FRAGMENT} step ${
                    invocationMessage.workflow_step_id + 1
                } requires a dataset, but dataset entered a failed state.`,
                hasStepPath: false,
            };
        }
    } else if (reason === "job_failed") {
        return {
            text: `${FAIL_FRAGMENT} step ${invocationMessage.workflow_step_id + 1} depends on job(s) created in step ${
                invocationMessage.dependent_workflow_step_id + 1
            }, but a job for that step failed.`,
            hasStepPath: false,
        };
    } else if (reason === "output_not_found") {
        return {
            text: `${FAIL_FRAGMENT} step ${invocationMessage.workflow_step_id + 1} depends on output '${
                invocationMessage.output_name
            }' of step ${
                invocationMessage.dependent_workflow_step_id + 1
            }, but this step did not produce an output of that name.`,
            hasStepPath: false,
        };
    } else if (reason === "expression_evaluation_failed") {
        return {
            prefix: `${FAIL_FRAGMENT}`,
            suffix: "contains an expression that could not be evaluated.",
            hasStepPath: true,
        };
    } else if (reason === "when_not_boolean") {
        return {
            prefix: `${FAIL_FRAGMENT}`,
            suffix: "is a conditional step and the result of the when expression is not a boolean type.",
            hasStepPath: true,
        };
    } else if (reason === "unexpected_failure") {
        if (invocationMessage.workflow_step_id !== null && invocationMessage.workflow_step_id !== undefined) {
            const details = invocationMessage.details ? `: '${invocationMessage.details}'` : ".";
            return {
                prefix: `${FAIL_FRAGMENT} an unexpected failure occurred at`,
                suffix: details,
                hasStepPath: true,
            };
        }
        const details = invocationMessage.details ? `: '${invocationMessage.details}'` : ".";
        return { text: `${FAIL_FRAGMENT} an unexpected failure occurred${details}`, hasStepPath: false };
    } else if (reason === "workflow_output_not_found") {
        return {
            prefix: `Defined workflow output '${invocationMessage.output_name}' was not found in`,
            suffix: ".",
            hasStepPath: true,
        };
    } else if (reason === "workflow_parameter_invalid") {
        return {
            prefix: "Workflow parameter on",
            suffix: `failed validation: ${invocationMessage.details}`,
            hasStepPath: true,
        };
    } else {
        return { text: reason, hasStepPath: false };
    }
});

// Fallback to simple string when no invocation data is available
const infoString = computed(() => {
    const info = messageInfo.value;
    if (info.hasStepPath) {
        const stepRef = buildStepPath(props.invocationMessage);
        return `${info.prefix} ${stepRef} ${info.suffix}`;
    }
    return info.text || "";
});
</script>

<template>
    <div :class="levelClass" style="text-align: center">
        <template v-if="messageInfo.hasStepPath && hasClickableStepPath">
            <span>{{ messageInfo.prefix }}</span>
            <span
                v-for="(stepInfo, index) in stepPathInfo"
                :key="`step-${index}-${stepInfo.isFinalStep ? 'final' : 'path'}`"
                class="step-path-container">
                <button class="step-badge clickable" @click="handleStepClick(stepInfo)">
                    {{ stepInfo.label }}
                </button>
                <span v-if="index < stepPathInfo.length - 1" class="step-arrow"> → </span>
            </span>
            <span>{{ messageInfo.suffix }}</span>
        </template>
        <template v-else>
            {{ infoString }}
        </template>
    </div>
</template>

<style scoped>
.step-path-container {
    display: inline;
}

.step-badge {
    display: inline-block;
    padding: 2px 8px;
    margin: 0 2px;
    border-radius: 4px;
    font-size: 0.9em;
    font-weight: 500;
}

.step-badge.clickable {
    background-color: #007bff;
    color: white;
    border: none;
    cursor: pointer;
    transition: background-color 0.2s;
}

.step-badge.clickable:hover {
    background-color: #0056b3;
    text-decoration: underline;
}

.step-arrow {
    color: inherit;
    margin: 0 4px;
}
</style>
