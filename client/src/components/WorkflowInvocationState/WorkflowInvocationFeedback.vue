<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { InvocationMessage, StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import { useInvocationStore } from "@/stores/invocationStore";

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
    // TODO: Implement a new backend API POST endpoint to handle the feedback submission for invocations.
    // One factor to consider here, how to check the user email for the workflow run?
    // For job runs we can do that via the `jobDetails.user_email` field, but for workflow runs we don't have that, I think...?
    return;
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

        <EmailReportForm class="mt-3" :submit="submit" />
    </div>
</template>
