<script setup lang="ts">
import { computed } from "vue";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import type { InvocationMessageResponseModel } from "./invocationMessageModel";
import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";
import WorkflowInvocationStep from "@/components/WorkflowInvocationState/WorkflowInvocationStep.vue";
import JobInformation from "@/components/JobInformation/JobInformation.vue";

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
};

const levelClasses = {
    warning: "warningmessage",
    cancel: "infomessage",
    error: "errormessage",
};

interface Invocation {
    workflow_id: string;
    state: string;
}

interface InvocationMessageProps {
    invocationMessage: InvocationMessageResponseModel;
    invocation: Invocation;
}

const props = defineProps<InvocationMessageProps>();
const levelClass = computed(() => levelClasses[level[props.invocationMessage.reason]]);

const workflow = computed(() => {
    if ("workflow_step_id" in props.invocationMessage) {
        const { workflow } = useWorkflowInstance(props.invocation.workflow_id);
        return workflow.value;
    }
    return undefined;
});

const workflowStep = computed(() => {
    if ("workflow_step_id" in props.invocationMessage && workflow.value) {
        return workflow.value.steps[props.invocationMessage.workflow_step_id];
    }
    return undefined;
});

const dependentWorkflowStep = computed(() => {
    if ("dependent_workflow_step_id" in props.invocationMessage && workflow.value) {
        const stepId = props.invocationMessage["dependent_workflow_step_id"];
        if (stepId !== undefined) {
            return workflow.value.steps[stepId];
        }
    }
    return undefined;
});

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
        throw "Unknown message level";
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
        return `${failFragment} an unexpected failure occurred.`;
    } else if (reason === "workflow_output_not_found") {
        return `Defined workflow output '${invocationMessage.output_name}' was not found in step ${
            invocationMessage.workflow_step_id + 1
        }.`;
    } else {
        return reason;
    }
});
</script>

<template>
    <div>
        <div :class="levelClass" style="text-align: center">
            {{ infoString }}
        </div>
        <div v-if="dependentWorkflowStep">
            Problem occurred at this step:
            <workflow-invocation-step
                :invocation="invocation"
                :workflow="workflow"
                :workflow-step="dependentWorkflowStep"></workflow-invocation-step>
        </div>
        <div v-if="workflowStep">
            {{ stepDescription }}
            <workflow-invocation-step
                :invocation="invocation"
                :workflow="workflow"
                :workflow-step="workflowStep"></workflow-invocation-step>
        </div>
        <div v-if="HdaId">
            This dataset failed:
            <generic-history-item :item-id="HdaId" item-src="hda" />
        </div>
        <div v-if="HdcaId">
            This dataset collection failed:
            <generic-history-item :item-id="HdcaId" item-src="hdca" />
        </div>
        <div v-if="jobId">
            This job failed:
            <job-information :job_id="jobId" />
        </div>
    </div>
</template>
