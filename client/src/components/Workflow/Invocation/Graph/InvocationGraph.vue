<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp, faSignInAlt, faSitemap, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCard, BCardBody, BCardHeader } from "bootstrap-vue";
import { computed, onUnmounted, ref, watch } from "vue";

import { components } from "@/api/schema";
import ExpandedItems from "@/components/History/Content/ExpandedItems";
import { JobProvider } from "@/components/providers";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useInvocationGraph } from "@/composables/useInvocationGraph";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type Step } from "@/stores/workflowStepStore";
import type { Workflow } from "@/stores/workflowStore";
import { withPrefix } from "@/utils/redirect";

import WorkflowInvocationSteps from "./WorkflowInvocationSteps.vue";
import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import JobInformation from "@/components/JobInformation/JobInformation.vue";
import JobParameters from "@/components/JobParameters/JobParameters.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

library.add(faChevronDown, faChevronUp, faSignInAlt, faSitemap, faTimes);

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
    /** Whether the parent component is visible */
    visible?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    zoom: 0.75,
    showMinimap: true,
    showZoomControls: true,
    initialX: -40,
    initialY: -40,
    visible: true,
});

const loadingGraph = ref(true);
const initialLoading = ref(true);
const errored = ref(false);
const errorMessage = ref("");
const showingJobId = ref<string | undefined>(undefined);
const pollTimeout = ref<any>(null);
const hideGraph = ref(false);

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

watch(
    () => props.zoom,
    () => (stateStore.scale = props.zoom),
    { immediate: true }
);

// on loading the steps, if any of the steps (an obj) has state === "error", toggleActiveNode
watch(
    () => initialLoading.value,
    (newVal) => {
        if (!newVal && steps.value) {
            const errorStep = Object.values(steps.value).find((step) => step.state === "error");
            if (errorStep) {
                stateStore.activeNodeId = errorStep.id;
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
        stateStore.activeNodeId = null;
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

function toggleActiveNode(stepId: number) {
    if (stateStore.activeNodeId === stepId) {
        stateStore.activeNodeId = null;
    } else {
        stateStore.activeNodeId = stepId;
    }
}

function getStepKey(step: Step) {
    return step.id;
}
</script>

<template>
    <div class="container-root w-100 overflow-auto d-flex flex-column">
        <BAlert v-if="initialLoading" show variant="info">
            <LoadingSpan message="Loading Invocation Graph" />
        </BAlert>
        <div v-else-if="errored">
            <BAlert v-if="errorMessage" show variant="danger">
                {{ errorMessage }}
            </BAlert>
            <BAlert v-else show variant="danger"> Unknown Error </BAlert>
        </div>
        <div v-else-if="visible && steps && datatypesMapper">
            <ExpandedItems
                explicit-key="expanded-invocation-steps"
                :scope-key="props.invocation.id"
                :get-item-key="getStepKey">
                <div class="d-flex">
                    <div v-if="!hideGraph" class="position-relative" style="width: 60%">
                        <BCard no-body>
                            <WorkflowGraph
                                :steps="steps"
                                :datatypes-mapper="datatypesMapper"
                                :initial-position="initialPosition"
                                :scroll-to-id="stateStore.activeNodeId"
                                :show-minimap="props.showMinimap"
                                :show-zoom-controls="props.showZoomControls"
                                is-invocation
                                readonly />
                        </BCard>
                        <BButton
                            class="position-absolute text-decoration-none m-2"
                            style="top: 0; right: 0"
                            size="sm"
                            @click="hideGraph = true">
                            <FontAwesomeIcon :icon="faTimes" class="mr-1" />
                            <span v-localize>Hide Graph</span>
                        </BButton>
                    </div>
                    <BButton v-else size="sm" class="p-0" @click="hideGraph = false">
                        <FontAwesomeIcon :icon="faSitemap" />
                        <div v-localize>Show Graph</div>
                    </BButton>
                    <WorkflowInvocationSteps
                        :steps="steps"
                        :store-id="storeId"
                        :invocation="invocationRef"
                        :workflow="props.workflow"
                        :hide-graph="hideGraph"
                        :showing-job-id="showingJobId || ''"
                        @update:showing-job-id="(jobId) => (showingJobId = jobId)"
                        @focus-on-step="toggleActiveNode" />
                </div>
            </ExpandedItems>
            <BCard v-if="showingJobId" class="mt-1" no-body>
                <BCardHeader class="d-flex justify-content-between align-items-center">
                    <Heading inline size="md">
                        Showing Job Details for
                        <ExternalLink :href="withPrefix(`/jobs/${showingJobId}/view`)">
                            <code>{{ showingJobId }}</code>
                        </ExternalLink>
                    </Heading>
                    <BButton variant="secondary" @click="showingJobId = undefined">
                        <FontAwesomeIcon :icon="faTimes" />
                    </BButton>
                </BCardHeader>
                <BCardBody>
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
</style>
