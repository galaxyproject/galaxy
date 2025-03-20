<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";

import { useActivityStore } from "@/stores/activityStore";
import { useWorkflowLandingStore } from "@/stores/workflowLandingStore";

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

const store = useWorkflowLandingStore();
const { claimWorkflow } = store;
const { claimState } = storeToRefs(store);

const activityStore = useActivityStore("default");

// Start claim immediately
claimWorkflow(props.uuid, props.public, props.secret).then(() => {
    activityStore.closeSideBar();
});
</script>

<template>
    <div>
        <div v-if="claimState.errorMessage">
            <BAlert variant="danger" show>
                {{ claimState.errorMessage }}
            </BAlert>
        </div>
        <div v-else-if="!claimState.workflowId">
            <LoadingSpan message="Loading workflow parameters" />
        </div>
        <div v-else>
            <WorkflowRun
                :workflow-id="claimState.workflowId"
                :prefer-simple-form="true"
                :request-state="claimState.requestState"
                :instance="claimState.instance" />
        </div>
    </div>
</template>
