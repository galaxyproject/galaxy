<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { components } from "@/api/schema";
import { isWorkflowInput } from "@/components/Workflow/constants";
import type { GraphStep } from "@/composables/useInvocationGraph";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Workflow } from "@/stores/workflowStore";

import WorkflowInvocationStep from "@/components/WorkflowInvocationState/WorkflowInvocationStep.vue";

library.add(faChevronDown, faChevronUp, faSignInAlt);

interface Props {
    /** The steps for the invocation graph */
    steps: { [index: string]: GraphStep };
    /** The store id for the invocation graph */
    storeId: string;
    /** The invocation to display */
    invocation: components["schemas"]["WorkflowInvocationElementView"];
    /** The workflow which was run */
    workflow: Workflow;
    /** Whether the invocation graph is hidden */
    hideGraph?: boolean;
    /** The id for the currently shown job */
    showingJobId: string;
    /** Whether the steps are being rendered on the dedicated invocation page/route */
    isFullPage?: boolean;
}

const emit = defineEmits<{
    (e: "focus-on-step", stepId: number): void;
    (e: "update:showing-job-id", value: string | undefined): void;
}>();

const props = withDefaults(defineProps<Props>(), {
    hideGraph: true,
});

const stepsDiv = ref<HTMLDivElement>();
const expandInvocationInputs = ref(false);

const stateStore = useWorkflowStateStore(props.storeId);
const { activeNodeId } = storeToRefs(stateStore);

const workflowInputSteps = Object.values(props.workflow.steps).filter((step) => isWorkflowInput(step.type));
const hasSingularInput = computed(() => workflowInputSteps.length === 1);
const workflowRemainingSteps = hasSingularInput.value
    ? Object.values(props.workflow.steps)
    : Object.values(props.workflow.steps).filter((step) => !isWorkflowInput(step.type));

watch(
    () => [activeNodeId.value, stepsDiv.value],
    async ([nodeId, card]) => {
        // on full page view, scroll to the active step card in the steps section
        if (props.isFullPage) {
            if (nodeId !== undefined && card) {
                // if the active node id is an input step, expand the inputs section, else, collapse it
                const isAnInput = workflowInputSteps.findIndex((step) => step.id === activeNodeId.value) !== -1;
                expandInvocationInputs.value = isAnInput;
                if (isAnInput) {
                    const inputHeader = stepsDiv.value?.querySelector(`.invocation-inputs-header`);
                    inputHeader?.scrollIntoView({ behavior: "smooth" });
                }

                // scroll to the active step card
                const stepCard = stepsDiv.value?.querySelector(`[data-index="${activeNodeId.value}"]`);
                stepCard?.scrollIntoView();
            }
        }
        // clear any job being shown
        emit("update:showing-job-id", undefined);
    },
    { immediate: true }
);

function showJob(jobId: string | undefined) {
    emit("update:showing-job-id", jobId);
}
</script>

<template>
    <div ref="stepsDiv" class="ml-2" :class="!props.hideGraph ? 'graph-steps-aside' : 'w-100'">
        <!-- Input Steps grouped in a separate portlet -->
        <div v-if="workflowInputSteps.length > 1" class="ui-portlet-section w-100">
            <div
                class="portlet-header portlet-operations invocation-inputs-header"
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

            <div v-if="expandInvocationInputs" class="portlet-content m-1">
                <WorkflowInvocationStep
                    v-for="step in workflowInputSteps"
                    :key="step.id"
                    :data-index="step.id"
                    :invocation="props.invocation"
                    :workflow="props.workflow"
                    :workflow-step="step"
                    :in-graph-view="!props.hideGraph"
                    :graph-step="steps[step.id]"
                    :expanded="props.hideGraph ? undefined : activeNodeId === step.id"
                    :showing-job-id="props.showingJobId"
                    @show-job="showJob"
                    @update:expanded="emit('focus-on-step', step.id)" />
            </div>
        </div>
        <!-- Non-Input (Tool/Subworkflow) Steps -->
        <WorkflowInvocationStep
            v-for="step in workflowRemainingSteps"
            :key="step.id"
            :data-index="step.id"
            :invocation="props.invocation"
            :workflow="props.workflow"
            :workflow-step="step"
            :in-graph-view="!props.hideGraph"
            :graph-step="steps[step.id]"
            :expanded="props.hideGraph ? undefined : activeNodeId === step.id"
            :showing-job-id="props.showingJobId"
            @show-job="showJob"
            @update:expanded="emit('focus-on-step', step.id)" />
    </div>
</template>

<style scoped>
.graph-steps-aside {
    overflow-y: scroll;
    scroll-behavior: smooth;
    width: 40%;
    max-height: 60vh;
}
</style>
