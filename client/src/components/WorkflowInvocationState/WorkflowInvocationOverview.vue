<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, ref } from "vue";
import { useRouter } from "vue-router/composables";

import type { InvocationMessage, StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

import InvocationGraph from "../Workflow/Invocation/Graph/InvocationGraph.vue";
import SubworkflowAlert from "./SubworkflowAlert.vue";
import WorkflowInvocationError from "./WorkflowInvocationError.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    invocation: WorkflowInvocationElementView;
    stepsJobsSummary?: StepJobSummary[];
    invocationAndJobTerminal: boolean;
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

function showSubworkflowInvocation(invocationId: string, stepId: number) {
    // Navigate to the subworkflow invocation page
    // The stepId parameter could be used to highlight a specific step, but for now
    // we'll just navigate to the subworkflow invocation
    router.push(`/workflows/invocations/${invocationId}`);
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
        <BAlert v-if="loading || !props.stepsJobsSummary" variant="info" show>
            <LoadingSpan message="Loading workflow..." />
        </BAlert>
        <BAlert v-else-if="error" variant="danger" show>
            {{ error }}
        </BAlert>
        <div v-else-if="workflow && !isSubworkflow">
            <InvocationGraph
                ref="invocationGraph"
                class="mt-1"
                data-description="workflow invocation graph"
                :invocation="invocation"
                :steps-jobs-summary="props.stepsJobsSummary"
                :workflow="workflow"
                :is-terminal="invocationAndJobTerminal"
                :is-full-page="isFullPage"
                :show-minimap="isFullPage" />
        </div>
        <BAlert v-else-if="!workflow" variant="info" show> No workflow found for this invocation. </BAlert>
    </div>
</template>
