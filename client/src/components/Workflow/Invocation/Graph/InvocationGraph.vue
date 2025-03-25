<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faArrowDown,
    faChevronDown,
    faChevronUp,
    faSignInAlt,
    faSitemap,
    faTimes,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { until } from "@vueuse/core";
import { BAlert, BButton, BCard, BCardBody, BCardHeader } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

import type { WorkflowInvocationElementView } from "@/api/invocations";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useInvocationGraph } from "@/composables/useInvocationGraph";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";
import WorkflowInvocationStep from "@/components/WorkflowInvocationState/WorkflowInvocationStep.vue";
import WorkflowInvocationStepHeader from "@/components/WorkflowInvocationState/WorkflowInvocationStepHeader.vue";

library.add(faArrowDown, faChevronDown, faChevronUp, faSignInAlt, faSitemap, faTimes);

interface Props {
    /** The invocation to display */
    invocation: WorkflowInvocationElementView;
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
const stepCard = ref<BCard | null>(null);
const loadedJobInfo = ref<typeof WorkflowInvocationStep | null>(null);
const workflowGraph = ref<InstanceType<typeof WorkflowGraph> | null>(null);

const invocationRef = computed(() => props.invocation);

const { datatypesMapper } = useDatatypesMapper();

const workflowId = computed(() => props.workflow?.id);
const workflowVersion = computed(() => props.workflow?.version);

const { steps, storeId, loadInvocationGraph, loading } = useInvocationGraph(
    invocationRef,
    workflowId.value,
    workflowVersion.value
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
    { immediate: true }
);

const stateStore = useWorkflowStateStore(storeId.value);
const { activeNodeId } = storeToRefs(stateStore);

watch(
    () => props.zoom,
    () => (stateStore.scale = props.zoom),
    { immediate: true }
);

onUnmounted(() => {
    clearTimeout(pollTimeout.value);
});

const initialPosition = computed(() => ({
    x: -props.initialX * props.zoom,
    y: -props.initialY * props.zoom,
}));

function activeStepFor(activeNodeId: number): Step {
    return props.workflow.steps[activeNodeId] as unknown as Step;
}

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
                <div class="position-relative w-100">
                    <BCard no-body>
                        <div v-if="activeNodeId !== null" class="overlay overlay-left" />
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
                        <div v-if="activeNodeId !== null" class="overlay overlay-right" />
                    </BCard>
                </div>
            </div>
            <BCard v-if="activeNodeId !== null" ref="stepCard" class="mt-2" no-body>
                <BCardHeader
                    class="d-flex justify-content-between align-items-center px-3 py-2"
                    :class="activeNodeId !== null ? steps[activeNodeId]?.headerClass : ''">
                    <WorkflowInvocationStepHeader
                        class="w-100 pr-2"
                        :workflow-step="activeStepFor(activeNodeId)"
                        :graph-step="steps[activeNodeId]"
                        :invocation-step="props.invocation.steps[activeNodeId]" />
                    <div class="d-flex flex-gapx-1">
                        <BButton title="Scroll to Step" size="sm" variant="link" @click="scrollStepToView()">
                            <FontAwesomeIcon :icon="faArrowDown" />
                        </BButton>
                        <BButton title="Hide Step" size="sm" variant="link" @click="activeNodeId = null">
                            <FontAwesomeIcon :icon="faTimes" />
                        </BButton>
                    </div>
                </BCardHeader>
                <BCardBody body-class="p-2">
                    <WorkflowInvocationStep
                        ref="loadedJobInfo"
                        :key="activeNodeId"
                        :invocation="props.invocation"
                        :workflow="props.workflow"
                        :workflow-step="props.workflow.steps[activeNodeId]"
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
@import "theme/blue.scss";

.container-root {
    container-type: inline-size;
}

.portlet-header {
    &:hover {
        opacity: 0.8;
    }
}

.overlay {
    bottom: 0;
    width: 1.5rem;
    background: rgba(200, 200, 200, 0.2);
    &.overlay-left {
        z-index: 1;
    }
    &.overlay-right {
        left: auto;
        right: 0;
    }
}

.graph-steps-aside {
    overflow-y: scroll;
    &.steps-fixed-height {
        max-height: 60vh;
    }
}

.invocation-graph {
    &:deep(.workflow-overview),
    &:deep(.zoom-control) {
        z-index: 100;
    }
}
</style>
