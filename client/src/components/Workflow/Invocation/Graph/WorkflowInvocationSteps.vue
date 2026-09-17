<script setup lang="ts">
import { faChevronDown, faChevronUp, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { getStepTitle } from "@/components/WorkflowInvocationState/util";
import { useInvocationGraph } from "@/composables/useInvocationGraph";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useToolStore } from "@/stores/toolStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import DelayedInput from "@/components/Common/DelayedInput.vue";
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

const { workflow, loading, error } = useWorkflowInstance(props.invocation.workflow_id);

const toolStore = useToolStore();
const workflowStore = useWorkflowStore();

const currentQuery = ref("");

const workflowId = computed(() => workflow.value?.id);
const workflowVersion = computed(() => workflow.value?.version);

const filteredWorkflowSteps = computed(() => {
    if (!workflow.value) {
        return [];
    }

    // If there is no search query, return all steps
    const steps = Object.values(workflow.value.steps);
    if (!currentQuery.value) {
        return steps;
    }

    // Filter steps based on the search query matching the step title
    const query = currentQuery.value.toLowerCase().trim();
    return steps.filter((step) => {
        const invocationStep = props.invocation.steps[step.id];

        const toolId = step.tool_uuid || step.tool_id;
        const toolName = toolId ? toolStore.getToolNameById(toolId) : undefined;
        const subworkflowName =
            "workflow_id" in step && step.workflow_id
                ? workflowStore.getStoredWorkflowByInstanceId(step.workflow_id)?.name
                : undefined;
        const title = getStepTitle(
            step.id,
            step.type,
            invocationStep?.workflow_step_label || undefined,
            toolName,
            subworkflowName,
        );
        return title.toLowerCase().includes(query);
    });
});

/** Workflow steps of the input type, filtered if there is a current query */
const workflowInputSteps = computed(() => filteredWorkflowSteps.value.filter((step) => isWorkflowInput(step.type)));

/** When there are 2+ inputs they are grouped in a collapsible portlet; otherwise inputs render inline. */
const oneOrNoInput = computed(() => workflowInputSteps.value.length <= 1);
const expandInvocationInputs = ref(false);

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

// Expand the inputs portlet while searching so results aren't hidden inside it
watch(
    () => currentQuery.value,
    (newVal) => {
        expandInvocationInputs.value = newVal.trim().length > 0;
    },
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
    <div v-else-if="graphSteps && workflow" class="steps-container">
        <div class="px-1 pt-1 pb-2">
            <DelayedInput placeholder="search steps" :delay="200" @change="(v) => (currentQuery = v)" />
        </div>

        <div v-if="filteredWorkflowSteps.length" class="steps-content">
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
            <div v-for="step in filteredWorkflowSteps" :key="step.id">
                <!-- TODO: This may or may not be needed (factor being how performant the step API calls are; seem pretty quick):
                    We potentially need to consider the fact that in this Steps view, we are constantly fetching all steps
                    until they are terminal, as opposed to the graph (Overview) view where we only fetch the singular step
                    that is visible. The advantage of this is that we can show reactive step status in the steps list without needing to
                    click into each step. If we only fetch expanded steps, the steps wouldn't update their status until clicked on.
                -->
                <WorkflowInvocationStep
                    v-if="!isWorkflowInput(step.type) || oneOrNoInput || expandInvocationInputs"
                    :class="{ 'mx-1': !oneOrNoInput && isWorkflowInput(step.type) }"
                    :data-index="step.id"
                    :invocation="props.invocation"
                    :workflow-step="step"
                    :graph-step="graphSteps[step.id]"
                    :expanded="undefined" />
            </div>
        </div>

        <BAlert v-else variant="info" show> No steps match the search query. </BAlert>
    </div>
    <BAlert v-else variant="info" show> There are no steps to display. </BAlert>
</template>

<style scoped lang="scss">
.steps-container {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    min-height: 0;
}

.steps-content {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    min-height: 0;
}
</style>
