<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faArrowLeft, faEdit, faExclamation, faHdd, faSitemap, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge, BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import { isRegisteredUser } from "@/api";
import type { InvocationJobsSummary, InvocationStep, WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useUserStore } from "@/stores/userStore";
import type { Workflow } from "@/stores/workflowStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { copyWorkflow } from "../Workflow/workflows.services";
import {
    errorCount as jobStatesSummaryErrorCount,
    jobCount as jobStatesSummaryJobCount,
    numTerminal,
    okCount as jobStatesSummaryOkCount,
    runningCount as jobStatesSummaryRunningCount,
} from "./util";

import AsyncButton from "../Common/AsyncButton.vue";
import Heading from "../Common/Heading.vue";
import SwitchToHistoryLink from "../History/SwitchToHistoryLink.vue";
import ProgressBar from "../ProgressBar.vue";
import UtcDate from "../UtcDate.vue";
import WorkflowInvocationsCount from "../Workflow/WorkflowInvocationsCount.vue";
import WorkflowRunButton from "../Workflow/WorkflowRunButton.vue";

interface Props {
    isFullPage?: boolean;
    invocation: WorkflowInvocationElementView;
    invocationState: string;
    fromPanel?: boolean;
    jobStatesSummary: InvocationJobsSummary;
    invocationSchedulingTerminal: boolean;
    invocationAndJobTerminal: boolean;
    success?: boolean;
    newHistoryTarget?: string;
}

const props = defineProps<Props>();

const { workflow } = useWorkflowInstance(props.invocation.workflow_id);

const { currentUser, isAnonymous } = storeToRefs(useUserStore());
const owned = computed(() => {
    if (isRegisteredUser(currentUser.value) && workflow.value) {
        return currentUser.value.username === workflow.value.owner;
    } else {
        return false;
    }
});

const importErrorMessage = ref<string | null>(null);
const importedWorkflow = ref<Workflow | null>(null);

async function onImport() {
    if (!workflow.value || !workflow.value.owner) {
        return;
    }
    try {
        const wf = await copyWorkflow(workflow.value.id, workflow.value.owner);
        importedWorkflow.value = wf as unknown as Workflow;
    } catch (error) {
        importErrorMessage.value = errorMessageAsString(error, "Failed to import workflow");
    }
}

function getWorkflowName(): string {
    return workflow.value?.name || "...";
}

type StepStateType = { [state: string]: number };

const stepStates = computed<StepStateType>(() => {
    const stepStates: StepStateType = {};
    const steps: InvocationStep[] = props.invocation.steps || [];
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
    return props.invocation.steps.length || 0;
});

const stepStatesStr = computed<string>(() => {
    return `${stepStates.value?.scheduled || 0} of ${stepCount.value} steps successfully scheduled.`;
});

const okCount = computed<number>(() => {
    return jobStatesSummaryOkCount(props.jobStatesSummary);
});

const runningCount = computed<number>(() => {
    return jobStatesSummaryRunningCount(props.jobStatesSummary);
});

const jobCount = computed<number>(() => {
    return jobStatesSummaryJobCount(props.jobStatesSummary);
});

const errorCount = computed<number>(() => {
    return jobStatesSummaryErrorCount(props.jobStatesSummary);
});

const newCount = computed<number>(() => {
    return jobCount.value - okCount.value - runningCount.value - errorCount.value;
});

const jobStatesStr = computed(() => {
    let jobStr = `${numTerminal(props.jobStatesSummary) || 0} of ${jobCount.value} jobs complete`;
    if (!props.invocationSchedulingTerminal) {
        jobStr += " (total number of jobs will change until all steps fully scheduled)";
    }
    return `${jobStr}.`;
});
</script>

<template>
    <div>
        <BAlert v-if="importErrorMessage" variant="danger" dismissible show @dismissed="importErrorMessage = null">
            {{ importErrorMessage }}
        </BAlert>
        <BAlert v-else-if="importedWorkflow" variant="info" dismissible show @dismissed="importedWorkflow = null">
            <span>
                Workflow <b>{{ importedWorkflow.name }}</b> imported successfully.
            </span>
            <RouterLink to="/workflows/list">Click here</RouterLink> to view the imported workflow in the workflows
            list.
        </BAlert>
        <div v-if="!props.success && props.isFullPage" class="d-flex flex-gapx-1">
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
        <div class="py-2 pl-3 d-flex justify-content-between align-items-center flex-nowrap">
            <div v-if="props.isFullPage">
                <i>
                    <FontAwesomeIcon :icon="faClock" class="mr-1" />invoked
                    <UtcDate :date="props.invocation.update_time" mode="elapsed" />
                </i>
                <span class="d-flex flex-gapx-1 align-items-center">
                    <FontAwesomeIcon :icon="faHdd" />History:
                    <SwitchToHistoryLink :history-id="props.invocation.history_id" />
                    <BBadge
                        v-if="props.newHistoryTarget"
                        v-b-tooltip.hover.noninteractive
                        role="button"
                        variant="info"
                        title="Results generated in a new history. Click on history name to switch to that history.">
                        <FontAwesomeIcon :icon="faExclamation" />
                    </BBadge>
                </span>
            </div>
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
                    :note="jobStatesStr"
                    :total="jobCount"
                    :ok-count="okCount"
                    :running-count="runningCount"
                    :new-count="newCount"
                    :error-count="errorCount"
                    :loading="!invocationAndJobTerminal"
                    class="jobs-progress" />
            </div>
            <div v-if="workflow" class="d-flex flex-gapx-1 align-items-center">
                <div class="d-flex flex-column align-items-end mr-2">
                    <span v-if="workflow.version !== undefined" class="mb-1">
                        <FontAwesomeIcon :icon="faSitemap" />
                        Workflow Version: {{ workflow.version + 1 }}
                    </span>
                    <WorkflowInvocationsCount class="float-right" :workflow="workflow" />
                </div>
                <BButtonGroup vertical>
                    <BButton
                        v-if="owned"
                        v-b-tooltip.hover.noninteractive.html
                        :title="
                            !workflow.deleted
                                ? `<b>Edit</b><br>${getWorkflowName()}`
                                : 'This workflow has been deleted.'
                        "
                        size="sm"
                        variant="secondary"
                        :disabled="workflow.deleted"
                        :to="`/workflows/edit?id=${workflow.id}&version=${workflow.version}`">
                        <FontAwesomeIcon :icon="faEdit" />
                        <span v-localize>Edit</span>
                    </BButton>
                    <AsyncButton
                        v-else
                        v-b-tooltip.hover.noninteractive
                        size="sm"
                        :disabled="isAnonymous"
                        :title="localize('Import this workflow')"
                        :icon="faUpload"
                        variant="outline-primary"
                        :action="onImport">
                        <span v-localize>Import</span>
                    </AsyncButton>
                    <WorkflowRunButton
                        :id="workflow.id || ''"
                        :title="
                            !workflow.deleted
                                ? `<b>Rerun</b><br>${getWorkflowName()}`
                                : 'This workflow has been deleted.'
                        "
                        :disabled="workflow.deleted"
                        full
                        force
                        :version="workflow.version" />
                </BButtonGroup>
            </div>
        </div>
    </div>
</template>

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
