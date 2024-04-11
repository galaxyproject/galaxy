<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BCard } from "bootstrap-vue";
import { computed, onUnmounted, ref, watch } from "vue";

import { components } from "@/api/schema";
import ExpandedItems from "@/components/History/Content/ExpandedItems";
import { JobProvider } from "@/components/providers";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useInvocationGraph } from "@/composables/useInvocationGraph";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type Step } from "@/stores/workflowStepStore";
import type { Workflow } from "@/stores/workflowStore";

import JobInformation from "@/components/JobInformation/JobInformation.vue";
import JobParameters from "@/components/JobParameters/JobParameters.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";
import WorkflowInvocationStep from "@/components/WorkflowInvocationState/WorkflowInvocationStep.vue";

library.add(faChevronDown, faChevronUp, faSignInAlt);

interface Props {
    /** The invocation to display */
    invocation: components["schemas"]["WorkflowInvocationElementView"];
    /** The workflow which was run */
    workflow: Workflow;
    /** Whether the invocation is terminal */
    isTerminal: boolean;
    /** Whether the invocation is scheduled */
    isScheduled: boolean;
    /** The zoom level for the graph */
    zoom?: number;
    /** Whether to show the minimap */
    showMinimap?: boolean;
    /** Whether to show the zoom controls */
    showZoomControls?: boolean;
    /** The initial x position for the graph */
    initialX?: number;
    /** The initial y position for the graph */
    initialY?: number;
}

const props = withDefaults(defineProps<Props>(), {
    zoom: 0.5,
    showMinimap: true,
    showZoomControls: true,
    initialX: -40,
    initialY: -40,
});

const loadingGraph = ref(true);
const initialLoading = ref(true);
const errored = ref(false);
const expandInvocationInputs = ref(false);
const errorMessage = ref("");
const showingJobId = ref<string | undefined>(undefined);
const scrollToId = ref<number | null>(null);
const pollTimeout = ref<any>(null);

const invocationRef = computed(() => props.invocation);

const { datatypesMapper } = useDatatypesMapper();

const workflowId = computed(() => props.workflow?.id);

const { steps, storeId, loadInvocationGraph } = useInvocationGraph(invocationRef, workflowId.value);

const workflowInputSteps = Object.values(props.workflow.steps).filter((step) => isWorkflowInput(step.type));

const workflowRemainingSteps = Object.values(props.workflow.steps).filter((step) => !isWorkflowInput(step.type));

// Equivalent to onMounted; this is where the graph is initialized, and the polling is started
watch(
    () => workflowId.value,
    async (wfId) => {
        if (wfId) {
            await pollInvocationGraph();
        }
    },
    { immediate: true }
);

const stateStore = useWorkflowStateStore(storeId.value);

watch(
    () => props.zoom,
    () => (stateStore.scale = props.zoom),
    { immediate: true }
);

watch(
    () => stateStore.activeNodeId,
    (newVal) => {
        if (newVal !== null) {
            // if the active node id is an input step, expand the inputs section
            expandInvocationInputs.value = workflowInputSteps.findIndex((step) => step.id === newVal) !== -1;
        }
        showingJobId.value = undefined;
    }
);

onUnmounted(() => {
    clearTimeout(pollTimeout.value);
});

const initialPosition = computed(() => ({
    x: -props.initialX * props.zoom,
    y: -props.initialY * props.zoom,
}));

/** Updates and loads the invocation graph */
async function loadGraph() {
    loadingGraph.value = true;
    errored.value = false;
    errorMessage.value = "";

    try {
        await loadInvocationGraph();
        errored.value = false;
    } catch (error: any) {
        if (error.response?.data.err_msg) {
            errorMessage.value = error.response.data.err_msg;
        } else {
            errorMessage.value = error as string;
        }
        errored.value = true;
    } finally {
        loadingGraph.value = false;
        if (initialLoading.value) {
            initialLoading.value = false;
        }
    }
}

/** Poll and load the invocation graph until the invocation is terminal */
async function pollInvocationGraph() {
    await loadGraph();
    if (!props.isTerminal) {
        pollTimeout.value = setTimeout(pollInvocationGraph, 3000);
    } else {
        clearTimeout(pollTimeout.value);
    }
}

function focusOnStep(stepId: number) {
    if (stateStore.activeNodeId === stepId) {
        stateStore.activeNodeId = null;
    } else {
        stateStore.activeNodeId = stepId;
        scrollToId.value = stepId;
    }
}

function getStepKey(step: Step) {
    return step.id;
}

function showStep(jobId: string) {
    showingJobId.value = jobId;
}
</script>

<template>
    <div id="center" class="container-root m-3 w-100 overflow-auto d-flex flex-column">
        <BAlert v-if="initialLoading" show variant="info">
            <LoadingSpan message="Loading Invocation Graph" />
        </BAlert>
        <div v-else-if="errored">
            <BAlert v-if="errorMessage" show variant="danger">
                {{ errorMessage }}
            </BAlert>
            <BAlert v-else show variant="danger"> Unknown Error </BAlert>
        </div>
        <div v-else-if="steps && datatypesMapper">
            <ExpandedItems
                explicit-key="expanded-invocation-steps"
                :scope-key="props.invocation.id"
                :get-item-key="getStepKey">
                <div class="workflow-invocation">
                    <div class="workflow-preview d-flex flex-column">
                        <BCard class="workflow-card">
                            <WorkflowGraph
                                :steps="steps"
                                :datatypes-mapper="datatypesMapper"
                                :initial-position="initialPosition"
                                :scroll-to-id="scrollToId"
                                :show-minimap="props.showMinimap"
                                :show-zoom-controls="props.showZoomControls"
                                is-invocation
                                readonly />
                        </BCard>
                    </div>
                    <BCard class="workflow-card">
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
                                <FontAwesomeIcon
                                    class="float-right"
                                    :icon="expandInvocationInputs ? faChevronUp : faChevronDown" />
                            </div>

                            <div v-if="expandInvocationInputs" class="portlet-content m-1">
                                <WorkflowInvocationStep
                                    v-for="step in workflowInputSteps"
                                    :key="step.id"
                                    :invocation="invocationRef"
                                    :workflow="props.workflow"
                                    :workflow-step="step"
                                    :graph-step="steps[step.id]"
                                    :expanded="stateStore.activeNodeId === step.id"
                                    :showing-job-id="showingJobId"
                                    @show-job="showStep"
                                    @update:expanded="focusOnStep(step.id)" />
                            </div>
                        </div>
                        <!-- Non-Input (Tool/Subworkflow) Steps -->
                        <WorkflowInvocationStep
                            v-for="step in workflowRemainingSteps"
                            :key="step.id"
                            :invocation="invocationRef"
                            :workflow="props.workflow"
                            :workflow-step="step"
                            :graph-step="steps[step.id]"
                            :expanded="stateStore.activeNodeId === step.id"
                            :showing-job-id="showingJobId"
                            @show-job="showStep"
                            @update:expanded="focusOnStep(step.id)" />
                    </BCard>
                </div>
            </ExpandedItems>
            <BCard v-if="showingJobId">
                <JobProvider :id="showingJobId" v-slot="{ item, loading }">
                    <div v-if="loading">
                        <LoadingSpan message="Loading Job Information" />
                    </div>
                    <div v-else>
                        <JobInformation v-if="item" :job_id="item.id" />
                        <p></p>
                        <JobParameters v-if="item" :job-id="item.id" :include-title="false" />
                    </div>
                </JobProvider>
            </BCard>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.container-root {
    container-type: inline-size;
}

.workflow-invocation {
    display: flex;
    flex-grow: 1;
    gap: 1rem;

    .workflow-preview {
        flex-grow: 1;

        .workflow-card {
            flex-grow: 1;
        }
    }
}

// TODO: This is a temporary fix for the invocation graph not fitting on smaller viewports
@container (max-width: 900px) {
    .workflow-invocation {
        flex-direction: column;
        height: unset;

        .workflow-preview {
            height: 450px;
        }
    }
}

.portlet-header {
    &:hover {
        opacity: 0.8;
    }
}
</style>
