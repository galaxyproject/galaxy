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
import { useElementBounding } from "@vueuse/core";
import { BAlert, BButton, BCard, BCardBody, BCardHeader } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onUnmounted, ref, watch } from "vue";

import type { LegacyWorkflowInvocationElementView } from "@/api/invocations";
import { JobProvider } from "@/components/providers";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useInvocationGraph } from "@/composables/useInvocationGraph";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Workflow } from "@/stores/workflowStore";
import { withPrefix } from "@/utils/redirect";

import WorkflowInvocationSteps from "./WorkflowInvocationSteps.vue";
import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import JobInformation from "@/components/JobInformation/JobInformation.vue";
import JobParameters from "@/components/JobParameters/JobParameters.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

library.add(faArrowDown, faChevronDown, faChevronUp, faSignInAlt, faSitemap, faTimes);

interface Props {
    /** The invocation to display */
    invocation: LegacyWorkflowInvocationElementView;
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
const showingJobId = ref<string | undefined>(undefined);
const pollTimeout = ref<any>(null);
const hideGraph = ref(false);
const jobCard = ref<BCard | null>(null);
const loadedJobInfo = ref<HTMLDivElement | null>(null);

const invocationRef = computed(() => props.invocation);

const { datatypesMapper } = useDatatypesMapper();

const workflowId = computed(() => props.workflow?.id);
const workflowVersion = computed(() => props.workflow?.version);

const { steps, storeId, loadInvocationGraph } = useInvocationGraph(
    invocationRef,
    workflowId.value,
    workflowVersion.value
);

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

// on loading steps, toggle the first one with state === "error" or last one if none are errored
watch(
    () => initialLoading.value,
    (newVal) => {
        if (!newVal && steps.value) {
            const errorStep = Object.values(steps.value).find((step) => step.state === "error");
            if (errorStep) {
                activeNodeId.value = errorStep.id;
            } else if (props.isTerminal) {
                activeNodeId.value = Object.values(steps.value)?.slice(-1)[0]?.id || null;
            }
        }
    },
    { immediate: true }
);

// when the graph is hidden/visible, reset the active node and showingJobId
watch(
    () => hideGraph.value,
    () => {
        showingJobId.value = undefined;
        activeNodeId.value = null;
    }
);

// scroll to the job card when it is loaded (only on invocation route)
if (props.isFullPage) {
    watch(
        () => loadedJobInfo.value,
        async (jobInfo) => {
            if (jobInfo) {
                scrollJobToView();
            }
        },
        { immediate: true }
    );
}

// properties for handling the flex-draggable steps panel
const invocationContainer = ref<HTMLDivElement | null>(null);
const { width: containerWidth } = useElementBounding(invocationContainer);
const minWidth = computed(() => containerWidth.value * 0.3);
const maxWidth = computed(() => 0.7 * containerWidth.value);

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

function scrollJobToView() {
    const jobCardHeader = jobCard.value?.querySelector(".card-header");
    jobCardHeader?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function toggleActiveStep(stepId: number) {
    if (activeNodeId.value === stepId) {
        activeNodeId.value = null;
    } else {
        activeNodeId.value = stepId;
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
            <div ref="invocationContainer" class="d-flex">
                <div v-if="!hideGraph" class="position-relative w-100">
                    <BCard no-body>
                        <WorkflowGraph
                            class="invocation-graph"
                            :steps="steps"
                            :datatypes-mapper="datatypesMapper"
                            :initial-position="initialPosition"
                            :scroll-to-id="activeNodeId"
                            :show-minimap="props.showMinimap"
                            :show-zoom-controls="props.showZoomControls"
                            is-invocation
                            readonly />
                    </BCard>
                    <BButton
                        class="position-absolute text-decoration-none m-2"
                        style="top: 0; right: 0"
                        data-description="hide invocation graph"
                        size="sm"
                        @click="hideGraph = true">
                        <FontAwesomeIcon :icon="faTimes" class="mr-1" />
                        <span v-localize>Hide Graph</span>
                    </BButton>
                </div>
                <BButton
                    v-else
                    v-b-tooltip.noninteractive.hover.right="'Show Graph'"
                    size="sm"
                    class="p-0"
                    style="width: min-content"
                    @click="hideGraph = false">
                    <FontAwesomeIcon :icon="faSitemap" />
                    <div v-localize>Show Graph</div>
                </BButton>
                <component
                    :is="!hideGraph ? FlexPanel : 'div'"
                    v-if="containerWidth"
                    side="right"
                    :collapsible="false"
                    class="ml-2"
                    :class="{ 'w-100': hideGraph }"
                    :min-width="minWidth"
                    :max-width="maxWidth"
                    :default-width="containerWidth * 0.4">
                    <WorkflowInvocationSteps
                        class="graph-steps-aside"
                        :class="{ 'steps-fixed-height': !hideGraph }"
                        :steps="steps"
                        :store-id="storeId"
                        :invocation="invocationRef"
                        :workflow="props.workflow"
                        :is-full-page="props.isFullPage"
                        :hide-graph="hideGraph"
                        :showing-job-id="showingJobId || ''"
                        :active-node-id="activeNodeId !== null ? activeNodeId : undefined"
                        @update:showing-job-id="(jobId) => (showingJobId = jobId)"
                        @focus-on-step="toggleActiveStep" />
                </component>
            </div>
            <BCard v-if="!hideGraph" ref="jobCard" class="mt-1" no-body>
                <BCardHeader class="d-flex justify-content-between align-items-center">
                    <Heading inline size="md">
                        <span v-if="showingJobId">
                            Showing Job Details for
                            <ExternalLink :href="withPrefix(`/jobs/${showingJobId}/view`)">
                                <code>{{ showingJobId }}</code>
                            </ExternalLink>
                        </span>
                        <span v-else>No Job Selected</span>
                    </Heading>
                    <div>
                        <BButton
                            v-if="showingJobId"
                            v-b-tooltip.hover.noninteractive
                            title="Scroll to Job"
                            @click="scrollJobToView()">
                            <FontAwesomeIcon :icon="faArrowDown" />
                        </BButton>
                        <BButton
                            v-if="showingJobId"
                            v-b-tooltip.hover.noninteractive
                            title="Hide Job"
                            @click="showingJobId = undefined">
                            <FontAwesomeIcon :icon="faTimes" />
                        </BButton>
                    </div>
                </BCardHeader>
                <BCardBody>
                    <JobProvider v-if="showingJobId" :id="showingJobId" v-slot="{ item, loading }">
                        <BAlert v-if="loading" show>
                            <LoadingSpan message="Loading Job Information" />
                        </BAlert>
                        <div v-else ref="loadedJobInfo">
                            <JobInformation v-if="item" :job_id="item.id" />
                            <p></p>
                            <JobParameters v-if="item" :job-id="item.id" :include-title="false" />
                        </div>
                    </JobProvider>
                    <BAlert v-else show>Select a job from a step in the invocation to view its details here.</BAlert>
                </BCardBody>
            </BCard>
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
