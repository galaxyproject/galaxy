<script setup lang="ts">
import { faExclamation, faSquare, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge, BButton, BTab, BTabs } from "bootstrap-vue";
import { computed, onUnmounted, ref, watch } from "vue";

import { type InvocationJobsSummary, type InvocationStep, type WorkflowInvocationElementView } from "@/api/invocations";
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

import ProgressBar from "../ProgressBar.vue";
import WorkflowInvocationSteps from "../Workflow/Invocation/Graph/WorkflowInvocationSteps.vue";
import InvocationReport from "../Workflow/InvocationReport.vue";
import WorkflowAnnotation from "../Workflow/WorkflowAnnotation.vue";
import WorkflowNavigationTitle from "../Workflow/WorkflowNavigationTitle.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";
import WorkflowInvocationInputOutputTabs from "./WorkflowInvocationInputOutputTabs.vue";
import WorkflowInvocationMetrics from "./WorkflowInvocationMetrics.vue";
import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    invocationId: string;
    isSubworkflow?: boolean;
    isFullPage?: boolean;
    success?: boolean;
    newHistoryTarget?: boolean;
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
        return `此工作流当前未被安排。当前状态为 ${state}。一旦工作流完全安排并且任务完成，所有禁用的标签将变为可用。`;
    } else if (runningCount.value != 0) {
        return `工作流调用仍包含 ${runningCount.value} 个正在运行的任务。一旦这些任务完成，所有禁用的标签将变为可用。`;
    } else {
        return "此工作流的步骤仍在运行。一旦完成，所有禁用的标签将变为可用。";
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
    if (invocationSchedulingTerminal.value && jobCount.value === 0) {
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
    return invocationState.value == "scheduled" && runningCount.value === 0 && invocationAndJobTerminal.value;
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

const okCount = computed<number>(() => {
    return jobStatesSummaryOkCount(jobStatesSummary.value);
});

const errorCount = computed<number>(() => {
    return jobStatesSummaryErrorCount(jobStatesSummary.value);
});

const runningCount = computed<number>(() => {
    return jobStatesSummaryRunningCount(jobStatesSummary.value);
});

const jobCount = computed<number>(() => {
    return jobStatesSummaryJobCount(jobStatesSummary.value);
});

const newCount = computed<number>(() => {
    return jobCount.value - okCount.value - runningCount.value - errorCount.value;
});

const jobStatesStr = computed(() => {
    let jobStr = `${numTerminal(jobStatesSummary.value) || 0} 个任务已完成，共 ${jobCount.value} 个任务`;
    if (!invocationSchedulingTerminal.value) {
        jobStr += " （直到所有步骤完全安排，任务总数将发生变化）";
    }
    return `${jobStr}。`;
});

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
    <div v-if="invocation" class="d-flex flex-column w-100" data-description="工作流调用状态">
        <WorkflowNavigationTitle
            v-if="props.isFullPage"
            :invocation="invocation"
            :workflow-id="invocation.workflow_id"
            :success="props.success">
            <template v-slot:workflow-title-actions>
                <BButton
                    v-if="!invocationAndJobTerminal"
                    v-b-tooltip.noninteractive.hover
                    title="取消安排工作流调用"
                    data-description="标题取消调用按钮"
                    size="sm"
                    class="text-decoration-none"
                    variant="link"
                    :disabled="cancellingInvocation || invocationState == 'cancelling'"
                    @click="onCancel">
                    <FontAwesomeIcon :icon="faSquare" fixed-width />
                    取消
                </BButton>
            </template>
        </WorkflowNavigationTitle>
        <WorkflowAnnotation
            v-if="props.isFullPage"
            :workflow-id="invocation.workflow_id"
            :invocation-update-time="invocation.update_time"
            :history-id="invocation.history_id"
            :new-history-target="props.newHistoryTarget">
            <template v-slot:middle-content>
                <div class="progress-bars mx-1">
                    <ProgressBar
                        v-if="!stepCount"
                        note="加载步骤状态汇总..."
                        :loading="true"
                        class="steps-progress" />
                    <ProgressBar
                        v-else-if="invocationState == 'cancelled'"
                        note="调用安排已取消 - 预期的任务和输出可能未生成。"
                        :error-count="1"
                        class="steps-progress" />
                    <ProgressBar
                        v-else-if="invocationState == 'failed'"
                        note="调用安排失败 - Galaxy 管理员可能在日志中提供更多细节。"
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
                        :note="jobStatesStr"
                        :total="jobCount"
                        :ok-count="okCount"
                        :running-count="runningCount"
                        :new-count="newCount"
                        :error-count="errorCount"
                        :loading="!invocationAndJobTerminal"
                        class="jobs-progress" />
                </div>
            </template>
        </WorkflowAnnotation>
        <BTabs
            ref="invocationTabs"
            class="mt-1 d-flex flex-column overflow-auto"
            :content-class="['overflow-auto', isScrollable ? 'pr-2' : '']">
            <BTab key="0" title="概览" active>
                <WorkflowInvocationOverview
                    class="invocation-overview"
                    :invocation="invocation"
                    :is-full-page="props.isFullPage"
                    :invocation-and-job-terminal="invocationAndJobTerminal"
                    :is-subworkflow="isSubworkflow" />
            </BTab>
            <BTab v-if="!isSubworkflow" title="步骤" lazy>
                <WorkflowInvocationSteps
                    v-if="invocation && storeId"
                    :invocation="invocation"
                    :store-id="storeId"
                    :is-full-page="props.isFullPage" />
            </BTab>
            <WorkflowInvocationInputOutputTabs :invocation="invocation" />
            <!-- <BTab title="工作流概览">
                <p>TODO: 在此插入工作流编辑器的只读版本</p>
            </BTab> -->
            <BTab
                v-if="!props.isSubworkflow"
                title="报告"
                title-item-class="invocation-report-tab"
                :disabled="tabsDisabled"
                :lazy="reportLazy"
                :active.sync="reportActive">
                <InvocationReport v-if="invocationStateSuccess" :invocation-id="invocation.id" />
            </BTab>
            <BTab title="导出" title-item-class="invocation-export-tab" :disabled="tabsDisabled" lazy>
                <div v-if="invocationAndJobTerminal">
                    <WorkflowInvocationExportOptions :invocation-id="invocation.id" />
                </div>
            </BTab>
            <BTab title="指标" :lazy="true">
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
                    <BButton
                        v-if="!props.isFullPage && !invocationAndJobTerminal"
                        v-b-tooltip.noninteractive.hover
                        class="my-1"
                        title="取消安排工作流调用"
                        data-description="取消调用按钮"
                        size="sm"
                        @click="onCancel">
                        <FontAwesomeIcon :icon="faTimes" fixed-width />
                        取消工作流
                    </BButton>
                </div>
            </template>
        </BTabs>
    </div>
    <BAlert v-else-if="errorMessage" variant="danger" show>
        {{ errorMessage }}
    </BAlert>
    <BAlert v-else-if="!invocationLoaded" variant="info" show>
        <LoadingSpan message="加载调用中" />
    </BAlert>
    <BAlert v-else variant="info" show>
        <span v-localize>未找到调用。</span>
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
