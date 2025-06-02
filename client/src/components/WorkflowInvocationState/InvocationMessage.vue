<script setup lang="ts">
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { InvocationMessage, WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

import GCard from "../Common/GCard.vue";
import WorkflowStepTitle from "./WorkflowStepTitle.vue";
import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";

type ReasonToLevel = {
    history_deleted: "cancel";
    user_request: "cancel";
    cancelled_on_review: "cancel";
    dataset_failed: "error";
    collection_failed: "error";
    job_failed: "error";
    output_not_found: "error";
    expression_evaluation_failed: "error";
    when_not_boolean: "error";
    unexpected_failure: "error";
    workflow_output_not_found: "warning";
    workflow_parameter_invalid: "error";
};

const level: ReasonToLevel = {
    history_deleted: "cancel",
    user_request: "cancel",
    cancelled_on_review: "cancel",
    dataset_failed: "error",
    collection_failed: "error",
    job_failed: "error",
    output_not_found: "error",
    expression_evaluation_failed: "error",
    when_not_boolean: "error",
    unexpected_failure: "error",
    workflow_output_not_found: "warning",
    workflow_parameter_invalid: "error",
};

const levelClasses = {
    warning: "warningmessage",
    cancel: "infomessage",
    error: "errormessage",
};

interface InvocationMessageProps {
    invocationMessage: InvocationMessage;
    invocation: WorkflowInvocationElementView;
}

const props = defineProps<InvocationMessageProps>();

const emit = defineEmits<{
    (e: "view-step", stepId: number): void;
}>();

const levelClass = computed(() => levelClasses[level[props.invocationMessage.reason]]);

const workflow = computed(() => {
    if ("workflow_step_id" in props.invocationMessage) {
        const { workflow } = useWorkflowInstance(props.invocation.workflow_id);
        return workflow.value;
    }
    return undefined;
});

const workflowStep = computed(() => {
    if (
        "workflow_step_id" in props.invocationMessage &&
        props.invocationMessage.workflow_step_id !== undefined &&
        props.invocationMessage.workflow_step_id !== null &&
        workflow.value
    ) {
        return workflow.value.steps[props.invocationMessage.workflow_step_id];
    }
    return undefined;
});
const invocationStep = computed(() => {
    if (workflowStep.value) {
        return props.invocation.steps[workflowStep.value.id];
    }
    return undefined;
});

const dependentWorkflowStep = computed(() => {
    if ("dependent_workflow_step_id" in props.invocationMessage && workflow.value) {
        const stepId = props.invocationMessage["dependent_workflow_step_id"];
        if (stepId !== undefined && stepId !== null) {
            return workflow.value.steps[stepId];
        }
    }
    return undefined;
});
const dependentInvocationStep = computed(() => {
    if (dependentWorkflowStep.value) {
        return props.invocation.steps[dependentWorkflowStep.value.id];
    }
    return undefined;
});

// This is used to indicate on the step cards whether the step is currently active in the invocation graph.\
const storeId = computed(() => `invocation-${props.invocation.id}`);
const stateStore = useWorkflowStateStore(storeId.value);
const { activeNodeId } = storeToRefs(stateStore);

const jobId = computed(() => "job_id" in props.invocationMessage && props.invocationMessage.job_id);
const HdaId = computed(() => "hda_id" in props.invocationMessage && props.invocationMessage.hda_id);
const HdcaId = computed(() => "hdca_id" in props.invocationMessage && props.invocationMessage.hdca_id);

const cancelFragment = "Invocation scheduling cancelled because";
const failFragment = "Invocation scheduling failed because ";
const stepDescription = computed(() => {
    const messageLevel = level[props.invocationMessage.reason];
    if (messageLevel === "warning") {
        return "This step caused a warning";
    } else if (messageLevel === "cancel") {
        return "This step canceled the invocation";
    } else if (messageLevel === "error") {
        return "This step failed the invocation";
    } else {
        throw Error("Unknown message level");
    }
});

const infoString = computed(() => {
    const invocationMessage = props.invocationMessage;
    const reason = invocationMessage.reason;
    if (reason === "user_request") {
        return `${cancelFragment} user requested cancellation.`;
    } else if (reason === "history_deleted") {
        return `${cancelFragment} the history of the invocation was deleted.`;
    } else if (reason === "cancelled_on_review") {
        return `${cancelFragment} the invocation was paused at step ${
            invocationMessage.workflow_step_id + 1
        } and not approved.`;
    } else if (reason === "collection_failed") {
        return `${failFragment} step ${
            invocationMessage.workflow_step_id + 1
        } requires a dataset collection created by step ${
            invocationMessage.dependent_workflow_step_id + 1
        }, but dataset collection entered a failed state.`;
    } else if (reason === "dataset_failed") {
        if (
            invocationMessage.dependent_workflow_step_id !== null &&
            invocationMessage.dependent_workflow_step_id !== undefined
        ) {
            return `${failFragment} step ${invocationMessage.workflow_step_id + 1} requires a dataset created by step ${
                invocationMessage.dependent_workflow_step_id + 1
            }, but dataset entered a failed state.`;
        } else {
            return `${failFragment} step ${
                invocationMessage.workflow_step_id + 1
            } requires a dataset, but dataset entered a failed state.`;
        }
    } else if (reason === "job_failed") {
        return `${failFragment} step ${invocationMessage.workflow_step_id + 1} depends on job(s) created in step ${
            invocationMessage.dependent_workflow_step_id + 1
        }, but a job for that step failed.`;
    } else if (reason === "output_not_found") {
        return `${failFragment} step ${invocationMessage.workflow_step_id + 1} depends on output '${
            invocationMessage.output_name
        }' of step ${
            invocationMessage.dependent_workflow_step_id + 1
        }, but this step did not produce an output of that name.`;
    } else if (reason === "expression_evaluation_failed") {
        return `${failFragment} step ${
            invocationMessage.workflow_step_id + 1
        } contains an expression that could not be evaluated.`;
    } else if (reason === "when_not_boolean") {
        return `${failFragment} step ${
            invocationMessage.workflow_step_id + 1
        } is a conditional step and the result of the when expression is not a boolean type.`;
    } else if (reason === "unexpected_failure") {
        let atStep = "";
        if (invocationMessage.workflow_step_id !== null && invocationMessage.workflow_step_id !== undefined) {
            atStep = ` at step ${invocationMessage.workflow_step_id + 1}`;
        }
        if (invocationMessage.details) {
            return `${failFragment} an unexpected failure occurred${atStep}: '${invocationMessage.details}'`;
        }
        return `${failFragment} an unexpected failure occurred${atStep}.`;
    } else if (reason === "workflow_output_not_found") {
        return `Defined workflow output '${invocationMessage.output_name}' was not found in step ${
            invocationMessage.workflow_step_id + 1
        }.`;
    } else if (reason === "workflow_parameter_invalid") {
        return `Workflow parameter on step ${invocationMessage.workflow_step_id + 1} failed validation: ${
            invocationMessage.details
        }`;
    } else {
        return reason;
    }
});

function openJobInNewTab(jobId: string) {
    const url = `/jobs/${jobId}/view`;
    window.open(url, "_blank");
}
</script>

<template>
    <div>
        <div :class="levelClass" style="text-align: center">
            {{ infoString }}
        </div>
        <div class="invocation-error-grid d-flex flex-wrap">
            <GCard
                v-if="dependentWorkflowStep"
                clickable
                :current="activeNodeId === dependentWorkflowStep.id"
                grid-view
                @click="emit('view-step', dependentWorkflowStep.id)">
                Problem occurred at this step:
                <strong>
                    <WorkflowStepTitle
                        :step-index="dependentWorkflowStep.id"
                        :step-label="
                            dependentInvocationStep?.workflow_step_label || `Step ${dependentWorkflowStep.id + 1}`
                        "
                        :step-type="dependentWorkflowStep.type"
                        :step-tool-id="dependentWorkflowStep.tool_id"
                        :step-subworkflow-id="
                            'workflow_id' in dependentWorkflowStep ? dependentWorkflowStep.workflow_id : null
                        " />
                </strong>
            </GCard>
            <GCard
                v-if="workflowStep"
                clickable
                :current="activeNodeId === workflowStep.id"
                grid-view
                @click="emit('view-step', workflowStep.id)">
                {{ stepDescription }}:
                <strong>
                    <WorkflowStepTitle
                        :step-index="workflowStep.id"
                        :step-label="invocationStep?.workflow_step_label || `Step ${workflowStep.id + 1}`"
                        :step-type="workflowStep.type"
                        :step-tool-id="workflowStep.tool_id"
                        :step-subworkflow-id="'workflow_id' in workflowStep ? workflowStep.workflow_id : null" />
                </strong>
            </GCard>
            <GCard v-if="HdaId" grid-view>
                This dataset failed:
                <GenericHistoryItem :item-id="HdaId" item-src="hda" />
            </GCard>
            <GCard v-if="HdcaId" grid-view>
                This dataset collection failed:
                <GenericHistoryItem :item-id="HdcaId" item-src="hdca" />
            </GCard>
            <GCard v-if="jobId" clickable grid-view @click="openJobInNewTab(jobId)">
                <span>
                    This job failed: <strong> {{ jobId }} </strong>
                </span>
                <i>
                    Click to view job details in a new tab
                    <FontAwesomeIcon :icon="faExternalLinkAlt" />
                </i>
            </GCard>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "_breakpoints.scss";

.invocation-error-grid {
    container: cards-list / inline-size;
}
</style>
