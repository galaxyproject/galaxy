<script setup lang="ts">
import { computed } from "vue";

import type { InvocationMessage } from "@/api/invocations";

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
}

const props = defineProps<Props>();

const levelClass = computed(() => LEVEL_CLASSES[INVOCATION_MSG_LEVEL[props.invocationMessage.reason]]);

const infoString = computed(() => {
    const invocationMessage = props.invocationMessage;
    const reason = invocationMessage.reason;
    if (reason === "user_request") {
        return `${CANCEL_FRAGMENT} user requested cancellation.`;
    } else if (reason === "history_deleted") {
        return `${CANCEL_FRAGMENT} the history of the invocation was deleted.`;
    } else if (reason === "cancelled_on_review") {
        return `${CANCEL_FRAGMENT} the invocation was paused at step ${
            invocationMessage.workflow_step_id + 1
        } and not approved.`;
    } else if (reason === "collection_failed") {
        return `${FAIL_FRAGMENT} step ${
            invocationMessage.workflow_step_id + 1
        } requires a dataset collection created by step ${
            invocationMessage.dependent_workflow_step_id + 1
        }, but dataset collection entered a failed state.`;
    } else if (reason === "dataset_failed") {
        if (
            invocationMessage.dependent_workflow_step_id !== null &&
            invocationMessage.dependent_workflow_step_id !== undefined
        ) {
            return `${FAIL_FRAGMENT} step ${
                invocationMessage.workflow_step_id + 1
            } requires a dataset created by step ${
                invocationMessage.dependent_workflow_step_id + 1
            }, but dataset entered a failed state.`;
        } else {
            return `${FAIL_FRAGMENT} step ${
                invocationMessage.workflow_step_id + 1
            } requires a dataset, but dataset entered a failed state.`;
        }
    } else if (reason === "job_failed") {
        return `${FAIL_FRAGMENT} step ${invocationMessage.workflow_step_id + 1} depends on job(s) created in step ${
            invocationMessage.dependent_workflow_step_id + 1
        }, but a job for that step failed.`;
    } else if (reason === "output_not_found") {
        return `${FAIL_FRAGMENT} step ${invocationMessage.workflow_step_id + 1} depends on output '${
            invocationMessage.output_name
        }' of step ${
            invocationMessage.dependent_workflow_step_id + 1
        }, but this step did not produce an output of that name.`;
    } else if (reason === "expression_evaluation_failed") {
        return `${FAIL_FRAGMENT} step ${
            invocationMessage.workflow_step_id + 1
        } contains an expression that could not be evaluated.`;
    } else if (reason === "when_not_boolean") {
        return `${FAIL_FRAGMENT} step ${
            invocationMessage.workflow_step_id + 1
        } is a conditional step and the result of the when expression is not a boolean type.`;
    } else if (reason === "unexpected_failure") {
        let atStep = "";
        if (invocationMessage.workflow_step_id !== null && invocationMessage.workflow_step_id !== undefined) {
            atStep = ` at step ${invocationMessage.workflow_step_id + 1}`;
        }
        if (invocationMessage.details) {
            return `${FAIL_FRAGMENT} an unexpected failure occurred${atStep}: '${invocationMessage.details}'`;
        }
        return `${FAIL_FRAGMENT} an unexpected failure occurred${atStep}.`;
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
</script>

<template>
    <div :class="levelClass" style="text-align: center">
        {{ infoString }}
    </div>
</template>
