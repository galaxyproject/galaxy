<script setup lang="ts">
import { faExclamation, faSquare, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge, BTab, BTabs } from "bootstrap-vue";
import { computed, onUnmounted, ref, watch } from "vue";

import type { InvocationStep, WorkflowInvocationElementView } from "@/api/invocations";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useInvocationStore } from "@/stores/invocationStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { errorMessageAsString } from "@/utils/simple-error";

import {
    errorCount as jobStatesSummaryErrorCount,
    isTerminal,
    jobCount as jobStatesSummaryJobCount,
    numTerminal,
    okCount as jobStatesSummaryOkCount,
    runningCount as jobStatesSummaryRunningCount,
} from "./util";

import GButton from "../BaseComponents/GButton.vue";
import ProgressBar from "../ProgressBar.vue";
import WorkflowInvocationSteps from "../Workflow/Invocation/Graph/WorkflowInvocationSteps.vue";
import InvocationReport from "../Workflow/InvocationReport.vue";
import WorkflowAnnotation from "../Workflow/WorkflowAnnotation.vue";
import WorkflowNavigationTitle from "../Workflow/WorkflowNavigationTitle.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";
import WorkflowInvocationInputOutputTabs from "./WorkflowInvocationInputOutputTabs.vue";
import WorkflowInvocationMetrics from "./WorkflowInvocationMetrics.vue";
import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";
import WorkflowInvocationShare from "./WorkflowInvocationShare.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    invocationId: string;
    isSubworkflow?: boolean;
    isFullPage?: boolean;
    success?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    isSubworkflow: false,
});

const emit = defineEmits<{
    (e: "invocation-cancelled"): void;
}>();

const invocationStore = useInvocationStore();

const stepStatesInterval = ref<any>(undefined);
const jobStatesInterval = ref<any>(undefined);
const invocationLoaded = ref(false);
const errorMessage = ref<string | null>(null);
const cancellingInvocation = ref(false);

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

const workflowStore = useWorkflowStore();
const tabsDisabled = computed(
    () =>
        !invocationStateSuccess.value ||
        !invocation.value ||
        !workflowStore.getStoredWorkflowByInstanceId(invocation.value.workflow_id)
);

/** Tooltip message for the a tab when it is disabled */
const disabledTabTooltip = computed(() => {
    const state = invocationState.value;
    if (state != "scheduled") {
        return `This workflow is not currently scheduled. The current state is ${state}. Once the workflow is fully scheduled and jobs have complete any disabled tabs will become available.`;
    } else if (stateCounts.value && stateCounts.value.runningCount != 0) {
        return `The workflow invocation still contains ${stateCounts.value.runningCount} running job(s). Once these jobs have completed any disabled tabs will become available.`;
    } else {
        return "Steps for this workflow are still running. Any disabled tabs will be available once complete.";
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
    // If the job states summary is null, we haven't fetched it yet
    // If the `populated_state` for the summary is `new`, we haven't finished scheduling all jobs
    if (jobStatesSummary.value === null || jobStatesSummary.value.populated_state === "new") {
        return false;
    }

    if (invocationSchedulingTerminal.value && jobCount.value === 0) {
        // no jobs for this invocation (think it has just subworkflows/inputs)
        return true;
    }
    return isTerminal(jobStatesSummary.value);
});
const jobStatesSummary = computed(() => invocationStore.getInvocationJobsSummaryById(props.invocationId));

/** The job summary for each step in the invocation */
const stepsJobsSummary = computed(() => {
    return invocationStore.getInvocationStepJobsSummaryById(props.invocationId);
});

const invocationStateSuccess = computed(() => {
    return (
        invocationState.value == "scheduled" && stateCounts.value?.runningCount === 0 && invocationAndJobTerminal.value
    );
});

type StepStateType = { [state: string]: number };

const stepStates = computed<StepStateType>(() => {
    const stepStates: StepStateType = {};
    const steps: InvocationStep[] = invocation.value?.steps || [];
    for (const step of steps) {
        if (!step) {
            continue;
        }
        // the API defined state here allowing null and undefined is odd...
        const stepState: string = step.state || "unknown";
        if (!stepStates[stepState]) {
            stepStates[stepState] = 1;
        } else {
            stepStates[stepState] += 1;
        }
    }
    return stepStates;
});

const stepCount = computed<number>(() => {
    return invocation.value?.steps.length || 0;
});

const stepStatesStr = computed<string>(() => {
    return `${stepStates.value?.scheduled || 0} of ${stepCount.value} steps successfully scheduled.`;
});

const stateCounts = computed<{
    okCount: number;
    errorCount: number;
    runningCount: number;
    newCount: number;
} | null>(() => {
    if (jobStatesSummary.value === null) {
        return null;
    }
    const okCount = jobStatesSummaryOkCount(jobStatesSummary.value);
    const errorCount = jobStatesSummaryErrorCount(jobStatesSummary.value);
    const runningCount = jobStatesSummaryRunningCount(jobStatesSummary.value);
    const newCount = jobCount.value - okCount - runningCount - errorCount;
    return { okCount, errorCount, runningCount, newCount };
});

const jobCount = computed<number>(() => {
    return jobStatesSummaryJobCount(jobStatesSummary.value);
});

const jobStatesStr = computed(() => {
    if (jobStatesSummary.value === null) {
        return "No jobs summary available yet.";
    }

    let jobStr = `${numTerminal(jobStatesSummary.value) || 0} of ${jobCount.value} jobs complete`;
    if (!invocationSchedulingTerminal.value) {
        jobStr += " (total number of jobs will change until all steps fully scheduled)";
    }
    return `${jobStr}.`;
});

watch(
    () => props.invocationId,
    async (id) => {
        invocationLoaded.value = false;
        try {
            await invocationStore.fetchInvocationById({ id });
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

watch(
    () => invocationSchedulingTerminal.value,
    async (newVal, oldVal) => {
        if (oldVal && !newVal) {
            // If the invocation was terminal and now is not, start polling again
            await pollStepStatesUntilTerminal();
        }
    }
);

onUnmounted(() => {
    clearTimeout(stepStatesInterval.value);
    clearTimeout(jobStatesInterval.value);
});

async function pollStepStatesUntilTerminal() {
    if (!invocationSchedulingTerminal.value) {
        await invocationStore.fetchInvocationById({ id: props.invocationId });
        stepStatesInterval.value = setTimeout(pollStepStatesUntilTerminal, 3000);
    }
}
async function pollJobStatesUntilTerminal() {
    if (!jobStatesTerminal.value) {
        await invocationStore.fetchInvocationJobsSummaryForId({ id: props.invocationId });
        await invocationStore.fetchInvocationStepJobsSummaryForId({ id: props.invocationId });
        jobStatesInterval.value = setTimeout(pollJobStatesUntilTerminal, 3000);
    }
}
function onError(e: any) {
    console.error(e);
}
async function onCancel() {
    try {
        cancellingInvocation.value = true;
        await invocationStore.cancelWorkflowScheduling(props.invocationId);
    } catch (e) {
        onError(e);
    } finally {
        emit("invocation-cancelled");
        cancellingInvocation.value = false;
    }
}
</script>

<template>
    <div v-if="invocation" class="d-flex flex-column w-100" data-description="workflow invocation state">
        <WorkflowNavigationTitle
            v-if="props.isFullPage"
            :invocation="invocation"
            :workflow-id="invocation.workflow_id"
            :success="props.success">
            <template v-slot:workflow-title-actions>
                <GButton
                    v-if="!invocationAndJobTerminal"
                    title="Cancel scheduling of workflow invocation"
                    tooltip
                    data-description="header cancel invocation button"
                    size="small"
                    transparent
                    color="blue"
                    :disabled="cancellingInvocation || invocationState == 'cancelling'"
                    @click="onCancel">
                    <FontAwesomeIcon :icon="faSquare" fixed-width />
                    Cancel
                </GButton>
                <WorkflowInvocationShare
                    :invocation-id="invocation.id"
                    :workflow-id="invocation.workflow_id"
                    :history-id="invocation.history_id" />
            </template>
        </WorkflowNavigationTitle>
        <WorkflowAnnotation
            v-if="props.isFullPage"
            :workflow-id="invocation.workflow_id"
            :invocation-update-time="invocation.update_time"
            :history-id="invocation.history_id">
            <template v-slot:middle-content>
                <div class="progress-bars mx-1">
                    <ProgressBar
                        v-if="!stepCount"
                        note="Loading step state summary..."
                        :loading="true"
                        class="steps-progress" />
                    <ProgressBar
                        v-else-if="invocationState == 'cancelled'"
                        note="Invocation scheduling cancelled - expected jobs and outputs may not be generated."
                        :error-count="1"
                        class="steps-progress" />
                    <ProgressBar
                        v-else-if="invocationState == 'failed'"
                        note="Invocation scheduling failed - Galaxy administrator may have additional details in logs."
                        :error-count="1"
                        class="steps-progress" />
                    <ProgressBar
                        v-else
                        :note="stepStatesStr"
                        :total="stepCount"
                        :ok-count="stepStates.scheduled"
                        :loading="!invocationSchedulingTerminal"
                        class="steps-progress" />
                    <ProgressBar
                        v-if="stateCounts"
                        :note="jobStatesStr"
                        :total="jobCount"
                        :ok-count="stateCounts.okCount"
                        :running-count="stateCounts.runningCount"
                        :new-count="stateCounts.newCount"
                        :error-count="stateCounts.errorCount"
                        :loading="!invocationAndJobTerminal"
                        class="jobs-progress" />
                </div>
            </template>
        </WorkflowAnnotation>
        <BTabs
            ref="invocationTabs"
            class="mt-1 d-flex flex-column overflow-auto"
            :content-class="['overflow-auto', isScrollable ? 'pr-2' : '']">
            <BTab key="0" title="Overview" active>
                <WorkflowInvocationOverview
                    class="invocation-overview"
                    :invocation="invocation"
                    :steps-jobs-summary="stepsJobsSummary || undefined"
                    :is-full-page="props.isFullPage"
                    :invocation-and-job-terminal="invocationAndJobTerminal"
                    :is-subworkflow="isSubworkflow" />
            </BTab>
            <BTab v-if="!isSubworkflow" title="Steps" lazy>
                <WorkflowInvocationSteps
                    v-if="invocation && storeId"
                    :invocation="invocation"
                    :store-id="storeId"
                    :is-full-page="props.isFullPage" />
            </BTab>
            <WorkflowInvocationInputOutputTabs :invocation="invocation" :terminal="invocationAndJobTerminal" />
            <BTab
                v-if="!props.isSubworkflow"
                title="Report"
                title-item-class="invocation-report-tab"
                :disabled="tabsDisabled"
                :lazy="reportLazy"
                :active.sync="reportActive">
                <InvocationReport v-if="invocationStateSuccess" :invocation-id="invocation.id" />
            </BTab>
            <BTab title="Export" title-item-class="invocation-export-tab" :disabled="tabsDisabled" lazy>
                <div v-if="invocationAndJobTerminal">
                    <WorkflowInvocationExportOptions :invocation-id="invocation.id" />
                </div>
            </BTab>
            <BTab title="Metrics" :lazy="true">
                <WorkflowInvocationMetrics :invocation-id="invocation.id" :not-terminal="!invocationAndJobTerminal" />
            </BTab>
            <template v-slot:tabs-end>
                <div class="ml-auto d-flex align-items-center">
                    <BBadge
                        v-if="tabsDisabled"
                        v-b-tooltip.hover.noninteractive
                        class="mr-1"
                        :title="disabledTabTooltip"
                        variant="primary">
                        <FontAwesomeIcon :icon="faExclamation" />
                    </BBadge>
                    <GButton
                        v-if="!props.isFullPage && !invocationAndJobTerminal"
                        tooltip
                        class="my-1"
                        title="Cancel scheduling of workflow invocation"
                        data-description="cancel invocation button"
                        size="small"
                        @click="onCancel">
                        <FontAwesomeIcon :icon="faTimes" fixed-width />
                        Cancel Workflow
                    </GButton>
                </div>
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

<style lang="scss">
// To show the tooltip on the disabled report tab badge
.invocation-report-tab,
.invocation-export-tab {
    .nav-link.disabled {
        background-color: #e9edf0;
    }
}
</style>

<style scoped lang="scss">
.progress-bars {
    // progress bar shrinks to fit divs on either side
    flex-grow: 1;
    flex-shrink: 1;
    max-width: 50%;

    .steps-progress,
    .jobs-progress {
        // truncate text in progress bars
        white-space: nowrap;
        overflow: hidden;
    }
}
</style>
