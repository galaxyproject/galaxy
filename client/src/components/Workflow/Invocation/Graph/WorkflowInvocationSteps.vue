<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, nextTick, ref, watch } from "vue";

import type { LegacyWorkflowInvocationElementView } from "@/api/invocations";
import { isWorkflowInput } from "@/components/Workflow/constants";
import type { GraphStep } from "@/composables/useInvocationGraph";
import type { Workflow } from "@/stores/workflowStore";

import WorkflowInvocationStep from "@/components/WorkflowInvocationState/WorkflowInvocationStep.vue";

library.add(faChevronDown, faChevronUp, faSignInAlt);

interface Props {
    /** The steps for the invocation graph */
    steps: { [index: string]: GraphStep };
    /** The store id for the invocation graph */
    storeId: string;
    /** The invocation to display */
    invocation: LegacyWorkflowInvocationElementView;
    /** The workflow which was run */
    workflow: Workflow;
    /** Whether the invocation graph is hidden */
    hideGraph?: boolean;
    /** The id for the currently shown job */
    showingJobId: string;
    /** Whether the steps are being rendered on the dedicated invocation page/route */
    isFullPage?: boolean;
    /** The active node on the graph */
    activeNodeId?: number;
}

const emit = defineEmits<{
    (e: "focus-on-step", stepId: number): void;
    (e: "update:showing-job-id", value: string | undefined): void;
}>();

const props = withDefaults(defineProps<Props>(), {
    hideGraph: true,
    activeNodeId: undefined,
});

const stepsDiv = ref<HTMLDivElement>();

const workflowInputSteps = Object.values(props.workflow.steps).filter((step) => isWorkflowInput(step.type));
const oneOrNoInput = computed(() => workflowInputSteps.length <= 1);
const expandInvocationInputs = ref(oneOrNoInput.value);

watch(
    () => [props.activeNodeId, stepsDiv.value],
    async ([nodeId, card]) => {
        // if the active node id is an input step, expand the inputs section if not already expanded
        if (!expandInvocationInputs.value) {
            const isAnInput = workflowInputSteps.findIndex((step) => step.id === props.activeNodeId) !== -1;
            expandInvocationInputs.value = isAnInput;
        }

        await nextTick();

        // on full page view, scroll to the active step card in the steps section
        if (props.isFullPage) {
            if (nodeId !== undefined && card) {
                // scroll to the active step card
                const stepCard = stepsDiv.value?.querySelector(`[data-index="${props.activeNodeId}"]`);
                stepCard?.scrollIntoView({ block: "nearest", inline: "start" });
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
    <div ref="stepsDiv" class="d-flex flex-column w-100">
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
        <div v-for="step in props.workflow.steps" :key="step.id">
            <WorkflowInvocationStep
                v-if="!isWorkflowInput(step.type) || (isWorkflowInput(step.type) && expandInvocationInputs)"
                :class="{ 'mx-1': !oneOrNoInput && isWorkflowInput(step.type) }"
                :data-index="step.id"
                :invocation="props.invocation"
                :workflow="props.workflow"
                :workflow-step="step"
                :in-graph-view="!props.hideGraph"
                :graph-step="steps[step.id]"
                :expanded="props.hideGraph ? undefined : props.activeNodeId === step.id"
                :showing-job-id="props.showingJobId"
                @show-job="showJob"
                @update:expanded="emit('focus-on-step', step.id)" />
        </div>
    </div>
</template>
