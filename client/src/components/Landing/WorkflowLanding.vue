<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import { useActivityStore } from "@/stores/activityStore";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowRun from "@/components/Workflow/Run/WorkflowRun.vue";

interface Props {
    uuid: string;
    secret?: string;
    public?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    secret: undefined,
    public: false,
});

const workflowId = ref<string | null>(null);
const errorMessage = ref<string | null>(null);
const requestState = ref<Record<string, never> | null>(null);
const instance = ref<boolean>(false);

const activityStore = useActivityStore("default");

onMounted(async() => {
    let claim;
    let claimError;
    if (props.public) {
        const { data, error } = await GalaxyApi().GET("/api/workflow_landings/{uuid}", {
            params: {
                path: { uuid: props.uuid },
            },
        });
        claim = data;
        claimError = error;
    } else {
        const { data, error } = await GalaxyApi().POST("/api/workflow_landings/{uuid}/claim", {
            params: {
                path: { uuid: props.uuid },
            },
            body: {
                client_secret: props.secret,
            },
        });
        claim = data;
        claimError = error;
    }
    if (claim) {
        workflowId.value = claim.workflow_id;
        instance.value = claim.workflow_target_type === "workflow";
        requestState.value = claim.request_state;
    } else {
        errorMessage.value = errorMessageAsString(claimError);
    }
    activityStore.closeSideBar();
});
</script>

<template>
    <div>
        <div v-if="errorMessage">
            <BAlert variant="danger" show>
                {{ errorMessage }}
            </BAlert>
        </div>
        <div v-else-if="!workflowId">
            <LoadingSpan message="Loading workflow parameters" />
        </div>
        <div v-else>
            <WorkflowRun
                :workflow-id="workflowId"
                :prefer-simple-form="true"
                :request-state="requestState"
                :instance="instance" />
        </div>
    </div>
</template>
