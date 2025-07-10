<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import type { InvocationMessage, StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import { useInvocationStore } from "@/stores/invocationStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { isWorkflowInput } from "../Workflow/constants";
import { errorCount } from "./util";

import EmailReportForm from "../Common/EmailReportForm.vue";
import LoadingSpan from "../LoadingSpan.vue";
import InvocationMessageView from "./InvocationMessage.vue";
import WorkflowInvocationStep from "./WorkflowInvocationStep.vue";

const props = defineProps<{
    invocationId: string;
    historyId: string;
    storeId: string;
    stepsJobsSummary: StepJobSummary[];
    invocation: WorkflowInvocationElementView;
    invocationMessages: InvocationMessage[];
}>();

const { graphStepsByStoreId } = storeToRefs(useInvocationStore());

const steps = computed(() => graphStepsByStoreId.value[props.storeId]);

const errorMessage = ref<string>("");

/** The user ID of the workflow invocation, set based on the history user ID. */
const invocationUserId = ref<string | null>(null);
const loadingUserId = ref<boolean>(true);

fetchHistoryUserId();

async function fetchHistoryUserId() {
    // Fetch the history user ID to check if the user is the owner of the workflow run.
    // This is used to determine if the feedback form should be shown.
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}", {
        params: {
            path: { history_id: props.historyId },
            query: { keys: "user_id" },
        },
    });

    if (error) {
        errorMessage.value = errorMessageAsString(error);
        loadingUserId.value = false;
        return;
    }
    invocationUserId.value = "user_id" in data && data.user_id ? data.user_id : null;
    loadingUserId.value = false;
}

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
            // And we confirm the current user is indeed sending the report in the child `EmailReportForm` component.
        },
    });

    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }

    return data.messages;
}
</script>

<template>
    <div>
        <BAlert v-if="errorMessage" variant="danger" show>
            <h2 class="alert-heading h-sm">Failed to send feedback for the workflow run.</h2>
            {{ errorMessage }}
        </BAlert>

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

        <BAlert v-if="loadingUserId" variant="info" show>
            <LoadingSpan message="Loading user details" />
        </BAlert>
        <EmailReportForm v-else class="mt-3" :user-id="invocationUserId" :submit="submit" />
    </div>
</template>
