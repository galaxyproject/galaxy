<script setup lang="ts">
import { faChevronDown, faChevronUp, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { useInvocationGraph } from "@/composables/useInvocationGraph";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";

import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowInvocationStep from "@/components/WorkflowInvocationState/WorkflowInvocationStep.vue";

const props = defineProps<{
    /** The invocation to display */
    invocation: WorkflowInvocationElementView;
    /** Whether the steps are being rendered on the dedicated invocation page/route */
    isFullPage?: boolean;
    /** The job summary for each step in the invocation */
    stepsJobsSummary: StepJobSummary[];
}>();

const stepsDiv = ref<HTMLDivElement>();

const { workflow, loading, error } = useWorkflowInstance(props.invocation.workflow_id);

const workflowId = computed(() => workflow.value?.id);
const workflowVersion = computed(() => workflow.value?.version);
const workflowInputSteps = workflow.value
    ? Object.values(workflow.value.steps).filter((step) => isWorkflowInput(step.type))
    : [];
const oneOrNoInput = computed(() => workflowInputSteps.length <= 1);
const expandInvocationInputs = ref(oneOrNoInput.value);

const {
    steps: graphSteps,
    loadInvocationGraph,
    loading: graphLoading,
} = useInvocationGraph(
    computed(() => props.invocation),
    computed(() => props.stepsJobsSummary),
    workflowId,
    workflowVersion,
);

watch(
    () => workflowId.value,
    (newVal) => {
        if (newVal) {
            loadInvocationGraph(false);
        }
    },
    { immediate: true },
);
</script>

<template>
    <BAlert v-if="loading || graphLoading" variant="info" show>
        <LoadingSpan message="Loading invocation steps" />
    </BAlert>
    <BAlert v-else-if="error" variant="danger" show>
        {{ error }}
    </BAlert>
    <div v-else-if="graphSteps && workflow" ref="stepsDiv" class="d-flex flex-column w-100">
        <!-- Input Steps grouped in a separate portlet -->
        <div v-if="!oneOrNoInput" class="ui-portlet-section w-100">
            <div
                class="portlet-header portlet-operations"
                role="button"
                tabindex="0"
                @keyup.enter="expandInvocationInputs = !expandInvocationInputs"
                @click="expandInvocationInputs = !expandInvocationInputs">
                <span :id="`step-icon-invocation-inputs-section`">
                    <FontAwesomeIcon class="portlet-title-icon" :icon="faSignInAlt" />
                </span>
                <span class="portlet-title-text">
                    <u v-localize class="step-title ml-2">Workflow Inputs</u>
                </span>
                <FontAwesomeIcon class="float-right" :icon="expandInvocationInputs ? faChevronUp : faChevronDown" />
            </div>
        </div>
        <div v-for="step in workflow.steps" :key="step.id">
            <!-- TODO: This may or may not be needed (factor being how performant the step API calls are; seem pretty quick):
                We potentially need to consider the fact that in this Steps view, we are constantly fetching all steps
                until they are terminal, as opposed to the graph (Overview) view where we only fetch the singular step
                that is visible. The advantage of this is that we can show reactive step status in the steps list without needing to
                click into each step. If we only fetch expanded steps, the steps wouldn't update their status until clicked on.
            -->
            <WorkflowInvocationStep
                v-if="!isWorkflowInput(step.type) || (isWorkflowInput(step.type) && expandInvocationInputs)"
                :class="{ 'mx-1': !oneOrNoInput && isWorkflowInput(step.type) }"
                :data-index="step.id"
                :invocation="props.invocation"
                :workflow-step="step"
                :graph-step="graphSteps[step.id]"
                :expanded="undefined" />
        </div>
    </div>
    <BAlert v-else variant="info" show> There are no steps to display. </BAlert>
</template>
