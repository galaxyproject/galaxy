<script setup lang="ts">
import { faArrowCircleLeft, faArrowCircleRight, faArrowDown, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { until } from "@vueuse/core";
import { BAlert, BCard, BCardBody, BCardHeader } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

import type { StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useInvocationGraph } from "@/composables/useInvocationGraph";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";
import WorkflowInvocationStep from "@/components/WorkflowInvocationState/WorkflowInvocationStep.vue";
import WorkflowInvocationStepHeader from "@/components/WorkflowInvocationState/WorkflowInvocationStepHeader.vue";

interface Props {
    /** The invocation to display */
    invocation: WorkflowInvocationElementView;
    /** The job summary for each step in the invocation */
    stepsJobsSummary: StepJobSummary[];
    /** The workflow which was run */
    workflow: StoredWorkflowDetailed;
    /** Whether the invocation is terminal */
    isTerminal: boolean;
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
    /** Whether the graph is being rendered on the dedicated invocation page/route */
    isFullPage?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    zoom: 0.75,
    showMinimap: true,
    showZoomControls: true,
    initialX: -40,
    initialY: -40,
    visible: true,
    isFullPage: false,
});

const loadingGraph = ref(true);
const initialLoading = ref(true);
const errored = ref(false);
const errorMessage = ref("");
const pollTimeout = ref<any>(null);
const showSideOverlay = ref(false);
const stepCard = ref<BCard | null>(null);
const loadedJobInfo = ref<typeof WorkflowInvocationStep | null>(null);
const workflowGraph = ref<InstanceType<typeof WorkflowGraph> | null>(null);

const { datatypesMapper } = useDatatypesMapper();

const workflowId = computed(() => props.workflow?.id);
const workflowVersion = computed(() => props.workflow?.version);

const { steps, storeId, loadInvocationGraph, loading } = useInvocationGraph(
    computed(() => props.invocation),
    computed(() => props.stepsJobsSummary),
    workflowId,
    workflowVersion,
);

onMounted(async () => {
    await until(loading).toBe(false);
    await nextTick();

    // @ts-ignore: TS2339 webpack dev issue. hopefully we can remove this with vite
    workflowGraph.value?.fitWorkflow(0.25, 1.5, 20.0);
});

// Equivalent to onMounted; this is where the graph is initialized, and the polling is started
watch(
    () => workflowId.value,
    async (wfId) => {
        if (wfId) {
            await pollInvocationGraph();
        }
    },
    { immediate: true },
);

const stateStore = useWorkflowStateStore(storeId.value);
const { activeNodeId } = storeToRefs(stateStore);

watch(
    () => props.zoom,
    () => (stateStore.scale = props.zoom),
    { immediate: true },
);

onUnmounted(() => {
    clearTimeout(pollTimeout.value);
});

const initialPosition = computed(() => ({
    x: -props.initialX * props.zoom,
    y: -props.initialY * props.zoom,
}));

const activeStep = computed(() => (activeNodeId.value !== null ? props.workflow.steps[activeNodeId.value] : undefined));

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

/** Moves to the next or previous step in the workflow (if possible) */
function navigateStep(direction: "previous" | "next") {
    const totalSteps = Object.keys(props.workflow.steps).length;

    if (activeNodeId.value !== null && totalSteps > 1) {
        if (direction === "next" && activeNodeId.value < totalSteps - 1) {
            activeNodeId.value += 1;
        } else if (direction === "previous" && activeNodeId.value > 0) {
            activeNodeId.value -= 1;
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

function scrollStepToView() {
    const stepCardHeader = stepCard.value?.querySelector(".card-header");
    stepCardHeader?.scrollIntoView({ behavior: "smooth", block: "start" });
}

/** On a repetition of the step clicked, scroll to the step */
function stepClicked(nodeId: number | null) {
    if (nodeId === activeNodeId.value) {
        scrollStepToView();
    }
}
</script>

<template>
    <div>
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
            <div class="d-flex">
                <!-- eslint-disable-next-line vuejs-accessibility/mouse-events-have-key-events, vuejs-accessibility/no-static-element-interactions -->
                <div
                    class="position-relative w-100"
                    @mouseover="showSideOverlay = true"
                    @mouseleave="showSideOverlay = false">
                    <BCard no-body>
                        <div
                            v-if="activeNodeId !== null && showSideOverlay"
                            class="graph-scroll-overlay overlay-left" />
                        <WorkflowGraph
                            ref="workflowGraph"
                            class="invocation-graph"
                            :steps="steps"
                            :datatypes-mapper="datatypesMapper"
                            :initial-position="initialPosition"
                            :scroll-to-id="activeNodeId"
                            :show-minimap="props.showMinimap"
                            :show-zoom-controls="props.showZoomControls"
                            :fixed-height="60"
                            is-invocation
                            readonly
                            @stepClicked="stepClicked" />
                        <div
                            v-if="activeNodeId !== null && showSideOverlay"
                            class="graph-scroll-overlay overlay-right" />
                    </BCard>
                </div>
            </div>
            <BCard v-if="activeNodeId !== null && activeStep" ref="stepCard" class="invocation-step-card mt-2" no-body>
                <BCardHeader
                    class="d-flex justify-content-between align-items-center px-3 py-1"
                    :class="activeNodeId !== null ? steps[activeNodeId]?.headerClass : ''">
                    <WorkflowInvocationStepHeader
                        class="w-100 pr-2"
                        :workflow-step="activeStep"
                        :graph-step="steps[activeNodeId]"
                        :invocation-step="props.invocation.steps[activeNodeId]" />
                    <div class="d-flex flex-gapx-1">
                        <GButton title="Scroll to Step" size="small" transparent @click="scrollStepToView()">
                            <FontAwesomeIcon :icon="faArrowDown" />
                        </GButton>
                        <GButtonGroup>
                            <GButton
                                title="Previous Step"
                                :disabled="activeNodeId === 0"
                                disabled-title="No Previous Step"
                                transparent
                                @click="navigateStep('previous')">
                                <FontAwesomeIcon :icon="faArrowCircleLeft" />
                                Prev
                            </GButton>
                            <GButton
                                title="Next Step"
                                :disabled="activeNodeId === Object.keys(props.workflow.steps).length - 1"
                                disabled-title="No More Steps"
                                transparent
                                @click="navigateStep('next')">
                                <FontAwesomeIcon :icon="faArrowCircleRight" />
                                Next
                            </GButton>
                        </GButtonGroup>
                        <GButton title="Hide Step" size="small" transparent @click="activeNodeId = null">
                            <FontAwesomeIcon :icon="faTimes" />
                        </GButton>
                    </div>
                </BCardHeader>
                <BCardBody body-class="p-2">
                    <WorkflowInvocationStep
                        ref="loadedJobInfo"
                        :key="activeNodeId"
                        :invocation="props.invocation"
                        :workflow-step="activeStep"
                        in-graph-view
                        :graph-step="steps[activeNodeId]"
                        expanded />
                </BCardBody>
            </BCard>
            <BAlert v-else class="mt-2" show>Click on a step in the workflow graph above to view its details.</BAlert>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.container-root {
    container-type: inline-size;
}

.portlet-header {
    &:hover {
        opacity: 0.8;
    }
}

.graph-scroll-overlay {
    bottom: 0;
    width: 1.5rem;
    background: $gray-200;
    opacity: 0.5;
    position: absolute;
    height: 100%;
    &.overlay-left {
        z-index: 1;
    }
    &.overlay-right {
        left: auto;
        right: 0;
    }
}

.invocation-graph {
    &:deep(.workflow-overview),
    &:deep(.zoom-control) {
        z-index: 100;
    }
}

.invocation-step-card {
    min-height: 500px;
}
</style>
