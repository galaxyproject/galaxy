<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArrowLeft, faClock, faEdit, faEye, faHdd, faPlay, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BButtonGroup, BTab, BTabs } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import { type InvocationJobsSummary, type WorkflowInvocationElementView } from "@/api/invocations";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useInvocationStore } from "@/stores/invocationStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { cancelWorkflowScheduling } from "./services";
import { isTerminal, jobCount, runningCount } from "./util";

import Heading from "../Common/Heading.vue";
import SwitchToHistoryLink from "../History/SwitchToHistoryLink.vue";
import UtcDate from "../UtcDate.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";
import WorkflowInvocationInputOutputTabs from "./WorkflowInvocationInputOutputTabs.vue";
import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import InvocationReport from "@/components/Workflow/InvocationReport.vue";
import WorkflowInvocationsCount from "@/components/Workflow/WorkflowInvocationsCount.vue";
import WorkflowRunButton from "@/components/Workflow/WorkflowRunButton.vue";

library.add(faArrowLeft, faClock, faEdit, faEye, faHdd, faPlay, faSitemap);

interface Props {
    invocationId: string;
    index?: number;
    isSubworkflow?: boolean;
    isFullPage?: boolean;
    fromPanel?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    index: undefined,
    isSubworkflow: false,
});

const emit = defineEmits<{
    (e: "invocation-cancelled"): void;
}>();

const invocationStore = useInvocationStore();

const stepStatesInterval = ref<any>(undefined);
const jobStatesInterval = ref<any>(undefined);
const initialLoading = ref(true);
const errorMessage = ref<string | null>(null);

// after the report tab is first activated, no longer lazy-render it from then on
const reportActive = ref(false);
const reportLazy = ref(true);
watch(
    () => reportActive.value,
    (newValue) => {
        if (newValue) {
            reportLazy.value = false;
        }
    }
);

const invocationTabs = ref<BTabs>();
const scrollableDiv = computed(() => invocationTabs.value?.$el.querySelector(".tab-content") as HTMLElement);
const isScrollable = ref(false);
useAnimationFrameResizeObserver(scrollableDiv, ({ clientSize, scrollSize }) => {
    isScrollable.value = scrollSize.height >= clientSize.height + 1;
});

const invocation = computed(() =>
    !initialLoading.value && !errorMessage.value
        ? (invocationStore.getInvocationById(props.invocationId) as WorkflowInvocationElementView)
        : null
);
const invocationState = computed(() => invocation.value?.state || "new");
const invocationAndJobTerminal = computed(() => invocationSchedulingTerminal.value && jobStatesTerminal.value);
const invocationSchedulingTerminal = computed(() => {
    return (
        invocationState.value == "scheduled" ||
        invocationState.value == "cancelled" ||
        invocationState.value == "failed"
    );
});
const jobStatesTerminal = computed(() => {
    if (invocationSchedulingTerminal.value && jobCount(jobStatesSummary.value as InvocationJobsSummary) === 0) {
        // no jobs for this invocation (think subworkflow or just inputs)
        return true;
    }
    return !!jobStatesSummary.value && isTerminal(jobStatesSummary.value as InvocationJobsSummary);
});
const jobStatesSummary = computed(() => {
    const jobsSummary = invocationStore.getInvocationJobsSummaryById(props.invocationId);
    return (!jobsSummary ? null : jobsSummary) as InvocationJobsSummary;
});
const invocationStateSuccess = computed(() => {
    return (
        invocationState.value == "scheduled" &&
        runningCount(jobStatesSummary.value) === 0 &&
        invocationAndJobTerminal.value
    );
});

const workflowStore = useWorkflowStore();

const isDeletedWorkflow = computed(() => getWorkflow()?.deleted === true);
const workflowVersion = computed(() => getWorkflow()?.version);

onMounted(async () => {
    try {
        await invocationStore.fetchInvocationForId({ id: props.invocationId });
        initialLoading.value = false;
        if (invocation.value) {
            await pollStepStatesUntilTerminal();
            await pollJobStatesUntilTerminal();
        }
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
    } finally {
        initialLoading.value = false;
    }
});

onUnmounted(() => {
    clearTimeout(stepStatesInterval.value);
    clearTimeout(jobStatesInterval.value);
});

async function pollStepStatesUntilTerminal() {
    if (!invocationSchedulingTerminal.value) {
        await invocationStore.fetchInvocationForId({ id: props.invocationId });
        stepStatesInterval.value = setTimeout(pollStepStatesUntilTerminal, 3000);
    }
}
async function pollJobStatesUntilTerminal() {
    if (!jobStatesTerminal.value) {
        await invocationStore.fetchInvocationJobsSummaryForId({ id: props.invocationId });
        jobStatesInterval.value = setTimeout(pollJobStatesUntilTerminal, 3000);
    }
}
function onError(e: any) {
    console.error(e);
}
function onCancel() {
    emit("invocation-cancelled");
}
function cancelWorkflowSchedulingLocal() {
    cancelWorkflowScheduling(props.invocationId).then(onCancel).catch(onError);
}

function getWorkflow() {
    return invocation.value?.workflow_id
        ? (workflowStore.getStoredWorkflowByInstanceId(
              invocation.value?.workflow_id
          ) as unknown as StoredWorkflowDetailed)
        : undefined;
}

function getWorkflowId() {
    return invocation.value?.workflow_id
        ? workflowStore.getStoredWorkflowIdByInstanceId(invocation.value?.workflow_id)
        : undefined;
}

function getWorkflowName() {
    return workflowStore.getStoredWorkflowNameByInstanceId(invocation.value?.workflow_id || "");
}
</script>

<template>
    <div v-if="invocation" class="d-flex flex-column w-100">
        <div v-if="props.isFullPage" class="d-flex flex-gapx-1">
            <Heading h1 separator inline truncate size="xl" class="flex-grow-1">
                Invoked Workflow: "{{ getWorkflowName() }}"
            </Heading>

            <div v-if="!props.fromPanel">
                <BButton
                    v-b-tooltip.hover.noninteractive
                    :title="localize('Return to Invocations List')"
                    class="text-nowrap"
                    size="sm"
                    variant="outline-primary"
                    to="/workflows/invocations">
                    <FontAwesomeIcon :icon="faArrowLeft" class="mr-1" />
                    <span v-localize>Invocations List</span>
                </BButton>
            </div>
        </div>
        <div v-if="props.isFullPage" class="py-2 pl-3 d-flex justify-content-between align-items-center">
            <div>
                <i>
                    <FontAwesomeIcon :icon="faClock" class="mr-1" />invoked
                    <UtcDate :date="invocation.update_time" mode="elapsed" />
                </i>
                <span class="d-flex flex-gapx-1 align-items-center">
                    <FontAwesomeIcon :icon="faHdd" />History:
                    <SwitchToHistoryLink :history-id="invocation.history_id" />
                </span>
            </div>
            <div v-if="getWorkflow()" class="d-flex flex-gapx-1 align-items-center">
                <div class="d-flex flex-column align-items-end mr-2">
                    <span v-if="workflowVersion !== undefined" class="mb-1">
                        <FontAwesomeIcon :icon="faSitemap" />
                        Workflow Version: {{ workflowVersion + 1 }}
                    </span>
                    <WorkflowInvocationsCount class="float-right" :workflow="getWorkflow()" />
                </div>
                <BButtonGroup vertical>
                    <BButton
                        v-b-tooltip.hover.noninteractive.html
                        :title="
                            !isDeletedWorkflow
                                ? `<b>Edit</b><br>${getWorkflowName()}`
                                : 'This workflow has been deleted.'
                        "
                        size="sm"
                        variant="secondary"
                        :disabled="isDeletedWorkflow"
                        :to="`/workflows/edit?id=${getWorkflowId()}&version=${workflowVersion}`">
                        <FontAwesomeIcon :icon="faEdit" />
                        <span v-localize>Edit</span>
                    </BButton>
                    <WorkflowRunButton
                        :id="getWorkflowId() || ''"
                        :title="
                            !isDeletedWorkflow
                                ? `<b>Rerun</b><br>${getWorkflowName()}`
                                : 'This workflow has been deleted.'
                        "
                        :disabled="isDeletedWorkflow"
                        full
                        :version="workflowVersion" />
                </BButtonGroup>
            </div>
        </div>
        <BTabs
            ref="invocationTabs"
            class="mt-1 d-flex flex-column overflow-auto"
            :content-class="['overflow-auto', isScrollable ? 'pr-2' : '']">
            <BTab key="0" title="Overview" active>
                <WorkflowInvocationOverview
                    class="invocation-overview"
                    :invocation="invocation"
                    :index="index"
                    :is-full-page="props.isFullPage"
                    :invocation-and-job-terminal="invocationAndJobTerminal"
                    :invocation-scheduling-terminal="invocationSchedulingTerminal"
                    :job-states-summary="jobStatesSummary"
                    :is-subworkflow="isSubworkflow"
                    @invocation-cancelled="cancelWorkflowSchedulingLocal" />
            </BTab>
            <WorkflowInvocationInputOutputTabs :invocation="invocation" />
            <!-- <BTab title="Workflow Overview">
                <p>TODO: Insert readonly version of workflow editor here</p>
            </BTab> -->
            <BTab
                title="Report"
                title-item-class="invocation-report-tab"
                :disabled="!invocationStateSuccess"
                :lazy="reportLazy"
                :active.sync="reportActive">
                <InvocationReport v-if="invocationStateSuccess" :invocation-id="invocation.id" />
            </BTab>
            <BTab title="Export" lazy>
                <div v-if="invocationAndJobTerminal">
                    <WorkflowInvocationExportOptions :invocation-id="invocation.id" />
                </div>
                <BAlert v-else variant="info" show>
                    <LoadingSpan message="Waiting to complete invocation" />
                </BAlert>
            </BTab>
        </BTabs>
    </div>
    <BAlert v-else-if="initialLoading" variant="info" show>
        <LoadingSpan message="Loading invocation" />
    </BAlert>
    <BAlert v-else-if="errorMessage" variant="danger" show>
        {{ errorMessage }}
    </BAlert>
    <BAlert v-else variant="info" show>
        <span v-localize>Invocation not found.</span>
    </BAlert>
</template>
