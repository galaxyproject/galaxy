<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BTab, BTabs } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { useRoute } from "vue-router/composables";

import { InvocationJobsSummary, WorkflowInvocationElementView } from "@/api/invocations";
import { useInvocationStore } from "@/stores/invocationStore";

import { cancelWorkflowScheduling } from "./services";
import { isTerminal, jobCount } from "./util";

import WorkflowInvocationDetails from "./WorkflowInvocationDetails.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";
import WorkflowInvocationSummary from "./WorkflowInvocationSummary.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faArrowLeft);

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
</script>

<template>
    <BTabs v-if="invocation" :class="{ 'position-relative': isInvocationRoute }">
        <BTab title="Summary" active>
            <WorkflowInvocationSummary
                class="invocation-summary"
                :invocation="invocation"
                :index="index"
                :invocation-and-job-terminal="invocationAndJobTerminal"
                :invocation-scheduling-terminal="invocationSchedulingTerminal"
                :job-states-summary="jobStatesSummary"
                :is-subworkflow="isSubworkflow"
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
        <RouterLink v-if="isInvocationRoute" to="/workflows/invocations">
            <BButton class="position-absolute text-decoration-none" style="top: 0; right: 0">
                <FontAwesomeIcon :icon="faArrowLeft" class="mr-1" />
                Go to Invocations List
            </BButton>
        </RouterLink>
    </BTabs>
    <BAlert v-else variant="info" show>
        <LoadingSpan message="Loading invocation" />
    </BAlert>
</template>
