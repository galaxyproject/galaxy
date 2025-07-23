<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { GalaxyApi } from "@/api";
import type { InvocationMessage, StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import { useInvocationStore } from "@/stores/invocationStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { isWorkflowInput } from "../Workflow/constants";
import { errorCount } from "./util";

import EmailReportForm from "../Common/EmailReportForm.vue";
import InvocationMessageView from "./InvocationMessage.vue";
import WorkflowInvocationStep from "./WorkflowInvocationStep.vue";

const props = defineProps<{
    invocationId: string;
    storeId: string;
    stepsJobsSummary: StepJobSummary[];
    invocation: WorkflowInvocationElementView;
    invocationMessages: InvocationMessage[];
}>();

const { graphStepsByStoreId } = storeToRefs(useInvocationStore());

const steps = computed(() => graphStepsByStoreId.value[props.storeId]);

const stepsWithErrors = computed(() => {
    if (steps.value) {
        return Object.entries(steps.value)
            .filter(([index, step]) => {
                if (!isWorkflowInput(step.type)) {
                    const invocationStep = props.invocation.steps[Number(index)];
                    let invocationStepSummary: StepJobSummary | undefined;
                    if (invocationStep) {
                        invocationStepSummary = props.stepsJobsSummary.find((stepJobSummary: StepJobSummary) => {
                            if (stepJobSummary.model === "ImplicitCollectionJobs") {
                                return stepJobSummary.id === invocationStep.implicit_collection_jobs_id;
                            } else {
                                return stepJobSummary.id === invocationStep.job_id;
                            }
                        });
                    }
                    if (invocationStepSummary) {
                        return errorCount(invocationStepSummary) > 0;
                    }
                }
                return false;
            })
            .map(([_, step]) => step);
    }
    return [];
});

async function submit(message: string): Promise<string[][] | undefined> {
    const { data, error } = await GalaxyApi().POST("/api/invocations/{invocation_id}/error", {
        params: {
            path: { invocation_id: props.invocation.id },
        },
        body: {
            invocation_id: props.invocation.id,
            message: message,
            // Not including the "email" key here, the backend endpoint will automatically use the current user's email.
        },
    });

    if (error) {
        // just pass the error message to the child component which already handles that
        return [[errorMessageAsString(error), "danger"]];
    }

    return data.messages;
}
</script>

<template>
    <div>
        <h3 class="h-lg mt-2">Workflow Run Feedback</h3>

        <p>
            <span v-localize>
                You can use the following information to troubleshoot any issues, and then report any concerns via the
                form below.
            </span>
        </p>

        <div v-if="props.invocationMessages.length">
            <h4 class="mb-3 h-md">Invocation Messages</h4>

            <p>
                <span v-localize>
                    The workflow invocation produced the following message{{
                        props.invocationMessages.length > 1 ? "s" : ""
                    }}:
                </span>
            </p>

            <InvocationMessageView
                v-for="message in props.invocationMessages"
                :key="message.reason"
                :invocation-message="message" />
        </div>

        <div v-if="steps && stepsWithErrors.length">
            <h4 class="mb-3 h-md">Steps with Errors</h4>

            <p>
                <span v-localize>
                    The following step{{ stepsWithErrors.length > 1 ? "s have" : " has" }} at least one failed job. You
                    can review {{ stepsWithErrors.length > 1 ? "each step" : "the step" }} for details.
                </span>
            </p>

            <div v-for="step in stepsWithErrors" :key="step.id">
                <WorkflowInvocationStep
                    :data-index="step.id"
                    :invocation="props.invocation"
                    :workflow-step="step"
                    :graph-step="steps[step.id]" />
            </div>
        </div>

        <EmailReportForm class="mt-3" require-login :submit="submit" />
    </div>
</template>
