<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, nextTick, ref } from "vue";
import { useRouter } from "vue-router";

import type { InvocationMessage, StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

import InvocationGraph from "../Workflow/Invocation/Graph/InvocationGraph.vue";
import SubworkflowAlert from "./SubworkflowAlert.vue";
import WorkflowInvocationError from "./WorkflowInvocationError.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    invocation: WorkflowInvocationElementView;
    stepsJobsSummary?: StepJobSummary[];
    isFullPage?: boolean;
    isSubworkflow?: boolean;
    invocationMessages?: InvocationMessage[];
}

const props = defineProps<Props>();

const { workflow, loading, error } = useWorkflowInstance(props.invocation.workflow_id);

const invocationGraph = ref<InstanceType<typeof InvocationGraph> | null>(null);
const router = useRouter();

// TODO: Refactor so that `storeId` is only defined here, and then used in all children components/composables.
const storeId = computed(() => `invocation-${props.invocation.id}`);
const stateStore = useWorkflowStateStore(storeId.value);
const { activeNodeId } = storeToRefs(stateStore);

async function showStep(stepId: number) {
    if (invocationGraph.value) {
        activeNodeId.value = stepId;
        await nextTick();
        const graphSelector = invocationGraph.value?.$el?.querySelector(".invocation-graph");
        graphSelector?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function showSubworkflowInvocation(invocationId: string, stepId?: number) {
    router.push({
        path: `/workflows/invocations/${invocationId}`,
        query: stepId === undefined ? {} : { step_index: String(stepId) },
    });
}
</script>

<template>
    <div class="mb-3 workflow-invocation-state-component">
        <SubworkflowAlert v-if="isSubworkflow" :invocation-id="props.invocation.id" :state="props.invocation.state" />
        <div v-if="props.invocationMessages?.length" class="d-flex align-items-center">
            <WorkflowInvocationError
                v-for="message in props.invocationMessages"
                :key="message.reason"
                class="steps-progress my-1 w-100"
                :invocation-message="message"
                :invocation="props.invocation"
                :store-id="storeId"
                @view-step="showStep"
                @view-subworkflow-invocation="showSubworkflowInvocation" />
        </div>
        <!-- Once the workflow for the invocation and step job summaries are loaded, display the graph -->
        <GAlert v-if="loading || !props.stepsJobsSummary" variant="info" show>
            <LoadingSpan message="Loading workflow..." />
        </GAlert>
        <GAlert v-else-if="error" variant="danger" show>
            {{ error }}
        </GAlert>
        <div v-else-if="workflow && !isSubworkflow">
            <InvocationGraph
                ref="invocationGraph"
                class="mt-1"
                data-description="workflow invocation graph"
                :invocation="invocation"
                :steps-jobs-summary="props.stepsJobsSummary"
                :workflow="workflow"
                :is-full-page="isFullPage"
                :show-minimap="isFullPage" />
        </div>
        <GAlert v-else-if="!workflow" variant="info" show> No workflow found for this invocation. </GAlert>
    </div>
</template>
