<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArrowLeft, faClock, faEdit, faEye, faHdd, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCard, BTab, BTabs } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router/composables";

import { InvocationJobsSummary, WorkflowInvocationElementView } from "@/api/invocations";
import { components } from "@/api/schema";
import { useInvocationStore } from "@/stores/invocationStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import localize from "@/utils/localization";

import { cancelWorkflowScheduling } from "./services";
import { isTerminal, jobCount } from "./util";

import Heading from "../Common/Heading.vue";
import SwitchToHistoryLink from "../History/SwitchToHistoryLink.vue";
import UtcDate from "../UtcDate.vue";
import WorkflowInvocationDetails from "./WorkflowInvocationDetails.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";
import WorkflowInvocationSummary from "./WorkflowInvocationSummary.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faArrowLeft, faClock, faEdit, faEye, faHdd, faSitemap);

type StoredWorkflowDetailed = components["schemas"]["StoredWorkflowDetailed"];

const TABS = {
    SUMMARY: 0,
    DETAILS: 1,
    EXPORT: 2,
};

interface Props {
    invocationId: string;
    index?: number;
    isSubworkflow?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    index: undefined,
    isSubworkflow: false,
});

const emit = defineEmits<{
    (e: "invocation-cancelled"): void;
}>();

const route = useRoute();

const invocationStore = useInvocationStore();

const stepStatesInterval = ref<any>(undefined);
const jobStatesInterval = ref<any>(undefined);
const activeTab = ref(TABS.SUMMARY);

const invocation = computed(
    () => invocationStore.getInvocationById(props.invocationId) as WorkflowInvocationElementView
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
const isInvocationRoute = computed(() => route.path.includes(`/workflows/invocations/${props.invocationId}`));

const workflowStore = useWorkflowStore();

const isDeletedWorkflow = computed(() => getWorkflow()?.deleted === true);
const workflowVersion = computed(() => getWorkflow()?.version);

onMounted(() => {
    pollStepStatesUntilTerminal();
    pollJobStatesUntilTerminal();
});

onUnmounted(() => {
    clearTimeout(stepStatesInterval.value);
    clearTimeout(jobStatesInterval.value);
});

async function pollStepStatesUntilTerminal() {
    if (!invocation.value || !invocationSchedulingTerminal.value) {
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
    return workflowStore.getStoredWorkflowNameByInstanceId(invocation.value?.workflow_id);
}
</script>

<template>
    <div v-if="invocation" class="d-flex flex-column w-100">
        <div v-if="isInvocationRoute" class="d-flex flex-gapx-1">
            <Heading h1 separator inline truncate size="xl" class="flex-grow-1">
                Invoked Workflow: "{{ getWorkflowName() }}"
            </Heading>

            <div>
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
        <BCard v-if="isInvocationRoute" class="py-2 px-3" no-body>
            <div class="d-flex justify-content-between align-items-center">
                <span class="d-flex flex-gapx-1 align-items-center">
                    <FontAwesomeIcon :icon="faHdd" />History:
                    <SwitchToHistoryLink :history-id="invocation.history_id" />
                </span>
                <i>
                    <FontAwesomeIcon :icon="faClock" class="mr-1" />invoked
                    <UtcDate :date="invocation.update_time" mode="elapsed" />
                </i>
                <div v-if="getWorkflow()" class="d-flex flex-gapx-1 align-items-center">
                    <span v-if="workflowVersion !== undefined" class="mr-2">
                        <FontAwesomeIcon :icon="faSitemap" />
                        Workflow Version: {{ workflowVersion + 1 }}
                    </span>
                    <BButton
                        v-b-tooltip.hover.html
                        :title="
                            !isDeletedWorkflow
                                ? `<b>Edit</b><br>${getWorkflowName()}`
                                : 'This workflow has been deleted.'
                        "
                        size="sm"
                        variant="secondary"
                        :disabled="isDeletedWorkflow"
                        :to="`/workflows/edit?id=${getWorkflowId()}`">
                        <FontAwesomeIcon :icon="faEdit" />
                        <span v-localize>Edit</span>
                    </BButton>
                </div>
            </div>
        </BCard>
        <BTabs v-model="activeTab" class="mt-1 d-flex flex-column overflow-auto" content-class="overflow-auto">
            <BTab title="Summary">
                <WorkflowInvocationSummary
                    class="invocation-summary"
                    :invocation="invocation"
                    :index="index"
                    :is-invocation-route="isInvocationRoute"
                    :invocation-and-job-terminal="invocationAndJobTerminal"
                    :invocation-scheduling-terminal="invocationSchedulingTerminal"
                    :job-states-summary="jobStatesSummary"
                    :is-subworkflow="isSubworkflow"
                    :visible="activeTab === TABS.SUMMARY"
                    @invocation-cancelled="cancelWorkflowSchedulingLocal" />
            </BTab>
            <BTab title="Details">
                <WorkflowInvocationDetails :invocation="invocation" />
            </BTab>
            <!-- <BTab title="Workflow Overview">
                <p>TODO: Insert readonly version of workflow editor here</p>
            </BTab> -->
            <BTab title="Export">
                <div v-if="invocationAndJobTerminal">
                    <WorkflowInvocationExportOptions :invocation-id="invocation.id" />
                </div>
                <BAlert v-else variant="info" show>
                    <LoadingSpan message="Waiting to complete invocation" />
                </BAlert>
            </BTab>
        </BTabs>
    </div>
    <BAlert v-else variant="info" show>
        <LoadingSpan message="Loading invocation" />
    </BAlert>
</template>
