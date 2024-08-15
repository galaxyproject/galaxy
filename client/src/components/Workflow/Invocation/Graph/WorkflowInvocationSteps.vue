<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { WorkflowInvocationElementView } from "@/api/invocations";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useInvocationStore } from "@/stores/invocationStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowInvocationStep from "@/components/WorkflowInvocationState/WorkflowInvocationStep.vue";

library.add(faChevronDown, faChevronUp, faSignInAlt);

const props = defineProps<{
    /** The store id for the invocation graph */
    storeId: string;
    /** The invocation to display */
    invocation: WorkflowInvocationElementView;
    /** Whether the steps are being rendered on the dedicated invocation page/route */
    isFullPage?: boolean;
}>();

const invocationStore = useInvocationStore();
const { graphStepsByStoreId } = storeToRefs(invocationStore);
const graphSteps = computed(() => graphStepsByStoreId.value[props.storeId]);

const stepsDiv = ref<HTMLDivElement>();

const { workflow, loading, error } = useWorkflowInstance(props.invocation.workflow_id);

const workflowInputSteps = workflow.value
    ? Object.values(workflow.value.steps).filter((step) => isWorkflowInput(step.type))
    : [];
const oneOrNoInput = computed(() => workflowInputSteps.length <= 1);
const expandInvocationInputs = ref(oneOrNoInput.value);
</script>

<template>
    <BAlert v-if="loading" variant="info" show>
        <LoadingSpan message="Loading workflow" />
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
            <WorkflowInvocationStep
                v-if="!isWorkflowInput(step.type) || (isWorkflowInput(step.type) && expandInvocationInputs)"
                :class="{ 'mx-1': !oneOrNoInput && isWorkflowInput(step.type) }"
                :data-index="step.id"
                :invocation="props.invocation"
                :workflow="workflow"
                :workflow-step="step"
                :graph-step="graphSteps[step.id]" />
        </div>
    </div>
    <BAlert v-else variant="info" show> There are no steps to display. </BAlert>
</template>
