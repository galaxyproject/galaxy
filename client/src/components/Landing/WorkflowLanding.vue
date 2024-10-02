<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import { type ClaimLandingPayload } from "@/api/landings";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowRun from "@/components/Workflow/Run/WorkflowRun.vue";

interface Props {
    uuid: string;
    secret?: string;
}

const props = withDefaults(defineProps<Props>(), {
    secret: undefined,
});

const workflowId = ref<string | null>(null);
const errorMessage = ref<string | null>(null);
const requestState = ref<Record<string, never> | null>(null);

onMounted(async () => {
    const payload: ClaimLandingPayload = {};
    if (props.secret) {
        payload["client_secret"] = props.secret;
    }

    const { data, error } = await GalaxyApi().POST("/api/workflow_landings/{uuid}/claim", {
        params: {
            path: { uuid: props.uuid },
        },
        body: payload,
    });
    if (data) {
        workflowId.value = data.workflow_id;
        requestState.value = data.request_state;
    } else {
        errorMessage.value = errorMessageAsString(error);
    }
    console.log(data);
});
</script>

<template>
    <div>
        <div v-if="!workflowId">
            <LoadingSpan message="Loading workflow parameters" />
        </div>
        <div v-else-if="errorMessage">
            <BAlert variant="danger" show>
                {{ errorMessage }}
            </BAlert>
        </div>
        <div v-else>
            <WorkflowRun :workflow-id="workflowId" :prefer-simple-form="true" :request-state="requestState" />
        </div>
    </div>
</template>
