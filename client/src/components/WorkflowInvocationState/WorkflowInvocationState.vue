<script setup lang="ts">
import { BAlert, BTab, BTabs } from "bootstrap-vue";
import { computed, onBeforeUnmount, onMounted, onUnmounted, ref, toRef, watch } from "vue";

import { type InvocationJobsSummary } from "@/api/invocations";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useInvocationStore } from "@/stores/invocationStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { cancelWorkflowScheduling } from "./services";
import { useInvocationState } from "./usesInvocationState";
import { isTerminal, jobCount, runningCount } from "./util";

import InvocationReport from "../Workflow/InvocationReport.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";
import WorkflowInvocationHeader from "./WorkflowInvocationHeader.vue";
import WorkflowInvocationInputOutputTabs from "./WorkflowInvocationInputOutputTabs.vue";
import WorkflowInvocationMetrics from "./WorkflowInvocationMetrics.vue";
import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

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

const invocationTabs = ref<BTabs>();
const scrollableDiv = computed(() => invocationTabs.value?.$el.querySelector(".tab-content") as HTMLElement);
const isScrollable = ref(false);
useAnimationFrameResizeObserver(scrollableDiv, ({ clientSize, scrollSize }) => {
    isScrollable.value = scrollSize.height >= clientSize.height + 1;
});

const invocationState = computed(() => invocation.value?.state || "new");
const jobStatesTerminal = computed(() => {
    if (invocationSchedulingTerminal.value && jobCount(jobStatesSummary.value as InvocationJobsSummary) === 0) {
        // no jobs for this invocation (think subworkflow or just inputs)
        return true;
    }
    return !!jobStatesSummary.value && isTerminal(jobStatesSummary.value as InvocationJobsSummary);
});
const invocationStateSuccess = computed(() => {
    return (
        invocationState.value == "scheduled" &&
        jobStatesSummary.value &&
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

const {
    invocation,
    invocationSchedulingTerminal,
    invocationAndJobTerminal,
    jobStatesSummary,
    monitorState,
    clearStateMonitor,
} = useInvocationState(toRef(props, "invocationId"), "legacy");

onMounted(monitorState);
onBeforeUnmount(clearStateMonitor);

function onError(e: unknown) {
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
        <WorkflowInvocationHeader v-if="props.isFullPage" :invocation="invocation" :from-panel="props.fromPanel" />
        <BTabs
            ref="invocationTabs"
            class="mt-1 d-flex flex-column overflow-auto"
            :content-class="['overflow-auto', isScrollable ? 'pr-2' : '']">
            <BTab key="0" title="Overview" active>
                <WorkflowInvocationOverview
                    v-if="jobStatesSummary"
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
