<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, ref } from "vue";

import type { InvocationMessage, StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { withPrefix } from "@/utils/redirect";

import ExternalLink from "../ExternalLink.vue";
import HelpText from "../Help/HelpText.vue";
import InvocationGraph from "../Workflow/Invocation/Graph/InvocationGraph.vue";
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
</script>

<template>
    <div class="mb-3 workflow-invocation-state-component">
        <BAlert v-if="isSubworkflow" variant="secondary" show>
            This subworkflow is
            <HelpText :uri="`galaxy.invocations.states.${invocation.state}`" :text="invocation.state" />.
            <ExternalLink :href="withPrefix(`/workflows/invocations/${invocation.id}`)"> Click here </ExternalLink>
            to view this subworkflow in graph view.
        </BAlert>
        <div v-if="props.invocationMessages?.length" class="d-flex align-items-center">
            <WorkflowInvocationError
                v-for="message in props.invocationMessages"
                :key="message.reason"
                class="steps-progress my-1 w-100"
                :invocation-message="message"
                :invocation="invocation"
                :store-id="storeId"
                @view-step="showStep" />
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
