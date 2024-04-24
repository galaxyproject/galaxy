<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCard } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { ref, watch } from "vue";

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
    isInvocationRoute?: boolean;
}

const emit = defineEmits<{
    (e: "focus-on-step", stepId: number): void;
    (e: "update:showing-job-id", value: string | undefined): void;
}>();

const props = withDefaults(defineProps<Props>(), {
    hideGraph: true,
});

const stepsCard = ref<BCard>();
const expandInvocationInputs = ref(false);

const stateStore = useWorkflowStateStore(props.storeId);
const { activeNodeId } = storeToRefs(stateStore);

const workflowInputSteps = Object.values(props.workflow.steps).filter((step) => isWorkflowInput(step.type));

const workflowRemainingSteps = Object.values(props.workflow.steps).filter((step) => !isWorkflowInput(step.type));

// on invocation route, scroll to the active step card in the steps section
if (props.isInvocationRoute) {
    watch(
        () => [activeNodeId.value, stepsCard.value],
        ([nodeId, card]) => {
            if (nodeId !== undefined && card) {
                // if the active node id is an input step, expand the inputs section, else, collapse it
                const isAnInput = workflowInputSteps.findIndex((step) => step.id === activeNodeId.value) !== -1;
                expandInvocationInputs.value = isAnInput;
                if (isAnInput) {
                    const inputHeader = stepsCard.value?.querySelector(`.portlet-header`);
                    inputHeader?.scrollIntoView({ behavior: "smooth" });
                }

                // scroll to the active step card
                const stepCard = stepsCard.value?.querySelector(`[data-index="${activeNodeId.value}"]`);
                stepCard?.scrollIntoView();
            }
            // clear any job being shown
            emit("update:showing-job-id", undefined);
        },
        { immediate: true }
    );
}

function showStep(jobId: string | undefined) {
    emit("update:showing-job-id", jobId);
}
</script>

<template>
    <BCard ref="stepsCard" class="ml-2" :class="!props.hideGraph ? 'graph-steps-aside overflow-auto' : 'w-100'" no-body>
        <!-- Input Steps grouped in a separate portlet -->
        <div v-if="workflowInputSteps.length > 0" class="ui-portlet-section w-100">
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
                    @show-job="showStep"
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
            @show-job="showStep"
            @update:expanded="emit('focus-on-step', step.id)" />
    </BCard>
</template>

<style scoped>
.graph-steps-aside {
    width: 40%;
    max-height: 60vh;
}
</style>
