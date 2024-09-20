<script setup lang="ts">
import { faDownload, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BNavItem, BTab, BTabs } from "bootstrap-vue";
import { computed, onUnmounted, ref, watch } from "vue";

import { type InvocationJobsSummary, type WorkflowInvocationElementView } from "@/api/invocations";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { getRootFromIndexLink } from "@/onload";
import { useInvocationStore } from "@/stores/invocationStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { cancelWorkflowScheduling } from "./services";
import { isTerminal, jobCount, runningCount } from "./util";

import WorkflowInvocationSteps from "../Workflow/Invocation/Graph/WorkflowInvocationSteps.vue";
import InvocationReport from "../Workflow/InvocationReport.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";
import WorkflowInvocationHeader from "./WorkflowInvocationHeader.vue";
import WorkflowInvocationInputOutputTabs from "./WorkflowInvocationInputOutputTabs.vue";
import WorkflowInvocationMetrics from "./WorkflowInvocationMetrics.vue";
import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    invocationId: string;
    isSubworkflow?: boolean;
    isFullPage?: boolean;
    fromPanel?: boolean;
    success?: boolean;
    newHistoryTarget?: string;
}

const props = withDefaults(defineProps<Props>(), {
    isSubworkflow: false,
    newHistoryTarget: undefined,
});

const emit = defineEmits<{
    (e: "invocation-cancelled"): void;
}>();

const invocationStore = useInvocationStore();

const stepStatesInterval = ref<any>(undefined);
const jobStatesInterval = ref<any>(undefined);
const invocationLoaded = ref(false);
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

// Report and PDF generation
const generatePdfTooltip = "Generate PDF report for this workflow invocation";
const invocationPdfLink = computed<string | null>(
    () => getRootFromIndexLink() + `api/invocations/${props.invocationId}/report.pdf`
);
const disabledReportTooltip = computed(() => {
    const state = invocationState.value;
    if (state != "scheduled") {
        return `This workflow is not currently scheduled. The current state is ${state}. Once the workflow is fully scheduled and jobs have complete this option will become available.`;
    } else if (runningCount(jobStatesSummary.value) != 0) {
        return `The workflow invocation still contains ${runningCount(
            jobStatesSummary.value
        )} running job(s). Once these jobs have completed this option will become available.`;
    } else {
        return "Steps for this workflow are still running. A report will be available once complete.";
    }
});

const invocationTabs = ref<BTabs>();
const scrollableDiv = computed(() => invocationTabs.value?.$el.querySelector(".tab-content") as HTMLElement);
const isScrollable = ref(false);
useAnimationFrameResizeObserver(scrollableDiv, ({ clientSize, scrollSize }) => {
    isScrollable.value = scrollSize.height >= clientSize.height + 1;
});

const invocation = computed(() =>
    invocationLoaded.value
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

watch(
    () => props.invocationId,
    async (id) => {
        invocationLoaded.value = false;
        try {
            await invocationStore.fetchInvocationForId({ id });
            invocationLoaded.value = true;
            // Only start polling if there is a valid invocation
            if (invocation.value) {
                await pollStepStatesUntilTerminal();
                await pollJobStatesUntilTerminal();
            }
        } catch (e) {
            errorMessage.value = errorMessageAsString(e);
        }
    },
    { immediate: true }
);

const storeId = computed(() => (invocation.value ? `invocation-${invocation.value.id}` : undefined));

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
</script>

<template>
    <div v-if="invocation" class="d-flex flex-column w-100">
        <WorkflowInvocationHeader
            :is-full-page="props.isFullPage"
            :invocation="invocation"
            :invocation-state="invocationState"
            :from-panel="props.fromPanel"
            :job-states-summary="jobStatesSummary"
            :success="props.success"
            :new-history-target="props.newHistoryTarget"
            :invocation-scheduling-terminal="invocationSchedulingTerminal"
            :invocation-and-job-terminal="invocationAndJobTerminal" />
        <BTabs
            ref="invocationTabs"
            class="mt-1 d-flex flex-column overflow-auto"
            :content-class="['overflow-auto', isScrollable ? 'pr-2' : '']">
            <BTab key="0" title="Overview" active>
                <WorkflowInvocationOverview
                    class="invocation-overview"
                    :invocation="invocation"
                    :is-full-page="props.isFullPage"
                    :invocation-and-job-terminal="invocationAndJobTerminal"
                    :invocation-scheduling-terminal="invocationSchedulingTerminal"
                    :is-subworkflow="isSubworkflow"
                    @invocation-cancelled="cancelWorkflowSchedulingLocal" />
            </BTab>
            <BTab v-if="!isSubworkflow" title="Steps" lazy>
                <WorkflowInvocationSteps
                    v-if="invocation && storeId"
                    :invocation="invocation"
                    :store-id="storeId"
                    :is-full-page="props.isFullPage" />
            </BTab>
            <WorkflowInvocationInputOutputTabs :invocation="invocation" />
            <!-- <BTab title="Workflow Overview">
                <p>TODO: Insert readonly version of workflow editor here</p>
            </BTab> -->
            <BTab
                v-if="!props.isSubworkflow"
                title="Report"
                title-item-class="invocation-report-tab"
                :disabled="
                    !invocationStateSuccess || !workflowStore.getStoredWorkflowByInstanceId(invocation.workflow_id)
                "
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
            <BTab title="Metrics" :lazy="true">
                <WorkflowInvocationMetrics :invocation-id="invocation.id"></WorkflowInvocationMetrics>
            </BTab>
            <template v-slot:tabs-end>
                <BNavItem v-if="!invocationAndJobTerminal" class="invocation-pdf-link ml-auto alert-info mr-1">
                    <LoadingSpan message="Waiting to complete invocation" />
                    <BButton
                        v-b-tooltip.noninteractive.hover
                        class="cancel-workflow-scheduling"
                        title="Cancel scheduling of workflow invocation"
                        size="sm"
                        variant="danger"
                        @click="onCancel">
                        <FontAwesomeIcon :icon="faTimes" fixed-width />
                        Cancel Workflow
                    </BButton>
                </BNavItem>
                <li
                    role="presentation"
                    class="nav-item align-self-center invocation-pdf-link mr-2"
                    :class="{ 'ml-auto': invocationAndJobTerminal }">
                    <BButton
                        v-b-tooltip.hover.bottom.noninteractive
                        :title="invocationStateSuccess ? generatePdfTooltip : disabledReportTooltip"
                        :disabled="!invocationStateSuccess"
                        :href="invocationPdfLink"
                        size="sm"
                        target="_blank">
                        <FontAwesomeIcon :icon="faDownload" fixed-width />
                        Generate PDF
                    </BButton>
                </li>
            </template>
        </BTabs>
    </div>
    <BAlert v-else-if="errorMessage" variant="danger" show>
        {{ errorMessage }}
    </BAlert>
    <BAlert v-else-if="!invocationLoaded" variant="info" show>
        <LoadingSpan message="Loading invocation" />
    </BAlert>
    <BAlert v-else variant="info" show>
        <span v-localize>Invocation not found.</span>
    </BAlert>
</template>
