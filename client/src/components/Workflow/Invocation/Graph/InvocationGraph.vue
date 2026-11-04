<script setup lang="ts">
import {
    faArrowCircleLeft,
    faArrowCircleRight,
    faArrowDown,
    faExpand,
    faEye,
    faTimes,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { until } from "@vueuse/core";
import { BCard, BCardBody, BCardHeader } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, ref, watch } from "vue";

import type { StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useInvocationGraph } from "@/composables/useInvocationGraph";
import { useUid } from "@/composables/utils/uid";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
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
    /** Fit the graph and step details to the page height instead of scrolling */
    fitToPage?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    zoom: 0.75,
    showMinimap: true,
    showZoomControls: true,
    initialX: -40,
    initialY: -40,
    visible: true,
    fitToPage: false,
});

const loadingGraph = ref(true);
const initialLoading = ref(true);
const errored = ref(false);
const errorMessage = ref("");
const showSideOverlay = ref(false);
const stepCard = ref<BCard | null>(null);
const stepExpanded = ref(false);
const stepModalTargetId = useUid("invocation-step-modal-");
const detailedViewEnabled = ref(false);
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

    // @ts-ignore: TS2339 component method not exposed in template ref type
    workflowGraph.value?.fitWorkflow(0.25, 1.0, 20.0);
});

// Equivalent to onMounted; this is where the graph is initialized. The graph then follows the
// `invocation` and `stepsJobsSummary` props, polled by the parent.
watch(
    () => workflowId.value,
    async (wfId) => {
        if (wfId) {
            await loadGraph();
        }
    },
    { immediate: true },
);

// Retry a failed load when the parent polls new data
watch(
    () => [props.invocation, props.stepsJobsSummary],
    async () => {
        if (errored.value && workflowId.value) {
            await loadGraph();
        }
    },
);

const stateStore = useWorkflowStateStore(storeId.value);
const { activeNodeId } = storeToRefs(stateStore);

// Close the expanded-step modal when the active step changes
watch(
    () => activeNodeId.value,
    () => {
        stepExpanded.value = false;
    },
);

watch(
    () => props.zoom,
    () => (stateStore.scale = props.zoom),
    { immediate: true },
);

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

function scrollStepToView() {
    if (!props.fitToPage) {
        const stepCardHeader = stepCard.value?.querySelector(".card-header");
        stepCardHeader?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

/** On a repetition of the step clicked, scroll to the step */
function stepClicked(nodeId: number | null) {
    if (nodeId === activeNodeId.value) {
        scrollStepToView();
    }
}

function toggleDetailedView() {
    detailedViewEnabled.value = !detailedViewEnabled.value;
}
</script>

<template>
    <div :class="{ 'fit-to-page': props.fitToPage }">
        <GAlert v-if="initialLoading" show variant="info">
            <LoadingSpan message="Loading Invocation Graph" />
        </GAlert>
        <div v-else-if="errored">
            <GAlert v-if="errorMessage" show variant="danger">
                {{ errorMessage }}
            </GAlert>
            <GAlert v-else show variant="danger"> Unknown Error </GAlert>
        </div>
        <div v-else-if="steps && datatypesMapper" class="graph-layout">
            <div class="d-flex graph-pane" :class="{ 'with-details': activeNodeId !== null && activeStep }">
                <!-- eslint-disable-next-line vuejs-accessibility/mouse-events-have-key-events, vuejs-accessibility/no-static-element-interactions -->
                <div
                    class="position-relative w-100 graph-wrapper"
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
                            :detailed-view="detailedViewEnabled"
                            :fixed-height="props.fitToPage ? undefined : 60"
                            is-invocation
                            readonly
                            @stepClicked="stepClicked" />
                        <div
                            v-if="activeNodeId !== null && showSideOverlay"
                            class="graph-scroll-overlay overlay-right" />
                    </BCard>

                    <GButton
                        v-if="activeNodeId !== null"
                        class="detailed-view-button"
                        tooltip
                        :title="
                            detailedViewEnabled
                                ? 'Hide step connections'
                                : 'Show the inputs and outputs of the selected step, including all connections leading in and out'
                        "
                        data-description="toggle step connections button"
                        size="small"
                        color="blue"
                        outline
                        :pressed="detailedViewEnabled"
                        @click="toggleDetailedView">
                        <FontAwesomeIcon :icon="faEye" fixed-width />
                        Show Connections
                    </GButton>
                </div>
            </div>
            <BCard v-if="activeNodeId !== null && activeStep" ref="stepCard" class="invocation-step-card mt-2" no-body>
                <BCardHeader class="invocation-step-header" :class="steps[activeNodeId]?.headerClass">
                    <WorkflowInvocationStepHeader
                        class="mr-2"
                        :workflow-step="activeStep"
                        :graph-step="steps[activeNodeId]"
                        :invocation-step="props.invocation.steps[activeNodeId]" />
                    <div class="d-flex flex-gapx-1">
                        <GButton
                            v-if="!props.fitToPage"
                            title="Scroll to Step"
                            size="small"
                            transparent
                            @click="scrollStepToView()">
                            <FontAwesomeIcon :icon="faArrowDown" />
                        </GButton>
                        <GButton
                            v-if="activeStep.type === 'tool'"
                            title="Expand Step"
                            data-description="invocation graph expand step button"
                            size="small"
                            transparent
                            @click="stepExpanded = true">
                            <FontAwesomeIcon :icon="faExpand" />
                        </GButton>
                        <GButtonGroup>
                            <GButton
                                title="Previous Step"
                                data-description="invocation graph previous step button"
                                :disabled="activeNodeId === 0"
                                disabled-title="No Previous Step"
                                transparent
                                @click="navigateStep('previous')">
                                <FontAwesomeIcon :icon="faArrowCircleLeft" />
                                Prev
                            </GButton>
                            <GButton
                                title="Next Step"
                                data-description="invocation graph next step button"
                                :disabled="activeNodeId === Object.keys(props.workflow.steps).length - 1"
                                disabled-title="No More Steps"
                                transparent
                                @click="navigateStep('next')">
                                <FontAwesomeIcon :icon="faArrowCircleRight" />
                                Next
                            </GButton>
                        </GButtonGroup>
                        <GButton
                            title="Hide Step"
                            data-description="invocation graph hide step button"
                            size="small"
                            transparent
                            @click="activeNodeId = null">
                            <FontAwesomeIcon :icon="faTimes" />
                        </GButton>
                    </div>
                </BCardHeader>
                <BCardBody body-class="p-2">
                    <Teleport :to="`#${stepModalTargetId}`" :disabled="!stepExpanded" defer>
                        <WorkflowInvocationStep
                            :key="activeNodeId"
                            :invocation="props.invocation"
                            :workflow-step="activeStep"
                            in-graph-view
                            :graph-step="steps[activeNodeId]"
                            expanded />
                    </Teleport>
                    <GAlert v-if="stepExpanded"> The step details are currently being shown in a modal. </GAlert>
                </BCardBody>
                <GModal
                    :show="stepExpanded"
                    fixed-height
                    size="medium"
                    data-description="invocation graph expanded step modal"
                    @close="stepExpanded = false">
                    <template v-slot:header>
                        <WorkflowInvocationStepHeader
                            class="mr-2"
                            :workflow-step="activeStep"
                            :graph-step="steps[activeNodeId]"
                            :invocation-step="props.invocation.steps[activeNodeId]" />
                    </template>
                    <div :id="stepModalTargetId" />
                </GModal>
            </BCard>
            <GAlert v-else class="mt-2" show>Click on a step in the workflow graph above to view its details.</GAlert>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";
@import "@/style/scss/mixins";

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

// Fit to page: graph fills the space, splits 50/50 with the step card, and only the step body scrolls.
.fit-to-page {
    @include fill-column;
    overflow: hidden;

    .graph-layout,
    .graph-wrapper,
    .graph-wrapper > .card {
        @include fill-column;
    }

    .graph-pane {
        flex: 1 1 0;
        min-height: 0;

        &.with-details {
            flex: 0 0 50%;
        }
    }

    .invocation-step-card {
        flex: 1 1 0;
        min-height: 0;

        .card-body {
            min-height: 0;
            overflow-y: auto;
            overflow-x: hidden;
        }
    }
}

.detailed-view-button {
    position: absolute;
    top: 1rem;
    right: 1rem;
    z-index: 150;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.invocation-step-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing) var(--spacing-4);
    position: sticky;
    top: 0;
    z-index: 100;
}
</style>
