<script setup lang="ts">
import { computed, ref, watch } from "vue";

import {
    refactor,
    type RefactorRequestAction,
    type RefactorResponse,
    type RefactorResponseActionExecution,
    type RefactorResponseActionExecutionMessage,
    type WorkflowVersion,
} from "@/api/workflows";
import { useConfirmDialog } from "@/composables/confirmDialog";

import GModal from "@/components/BaseComponents/GModal.vue";

/** Messages that only report what happened, rather than something the workflow would lose. */
const INFORMATIONAL_MESSAGE_TYPES = ["subworkflow_up_to_date"];

interface Props {
    refactorActions: RefactorRequestAction[];
    versions: WorkflowVersion[];
    workflowId: string;
    title?: string;
    message?: string;
    version?: number;
}
const props = withDefaults(defineProps<Props>(), {
    title: "Issues reworking this workflow",
    message: "Please review the following potential issues...",
    version: undefined,
});

const emit = defineEmits<{
    (e: "onShow"): void;
    (e: "onWorkflowMessage", message: string, type: string): void;
    (e: "onWorkflowError", message: string, response: any): void;
    (e: "onRefactor", data: RefactorResponse): void;
}>();

const show = ref(props.refactorActions.length > 0);
const confirmActionExecutions = ref<RefactorResponseActionExecution[]>([]);
/** True while reporting a refactoring that would not change anything, so there is nothing to confirm. */
const nothingToApply = ref(false);

const { confirm } = useConfirmDialog();

/** Determines if the current version is not the latest */
const isNotLatestVersion = computed(
    () =>
        (props.version === 0 || props.version) &&
        props.versions.length > 1 &&
        props.version !== props.versions[props.versions.length - 1]?.version,
);

watch(
    () => props.refactorActions,
    (newActions) => {
        if (newActions.length > 0) {
            dryRun();
        }
    },
);

watch(show, (newShow) => {
    if (newShow) {
        // emit that this is showing, so the workflow editor
        // can hide modal.
        emit("onShow");
    }
});

async function dryRun() {
    if (isNotLatestVersion.value) {
        const contDryRun = await confirm(
            `This workflow is not the latest version. A refactor will be attempted on the specified "Version ${props.version! + 1}". Do you wish to continue?`,
            {
                title: "Confirm Refactor on Older Version",
                okText: `Yes, refactor "Version ${props.version! + 1}"`,
                cancelText: "No, cancel refactor",
            },
        );
        if (!contDryRun) {
            return;
        }
    }

    emit("onWorkflowMessage", "Pre-checking requested workflow changes (dry run)...", "progress");
    try {
        const data = await refactor(props.workflowId, props.refactorActions, "editor", true, props.version);
        onDryRunResponse(data);
    } catch (response) {
        onError(response as string);
    }
}

function onError(response: string) {
    emit("onWorkflowError", "Reworking workflow failed...", response);
}

function isInformational(message: RefactorResponseActionExecutionMessage) {
    return INFORMATIONAL_MESSAGE_TYPES.includes(message.message_type);
}

function onDryRunResponse(data: RefactorResponse) {
    const actionExecutions = data.action_executions;
    const messages = actionExecutions.flatMap((execution: RefactorResponseActionExecution) => execution.messages);
    if (messages.some((message) => !isInformational(message))) {
        nothingToApply.value = false;
        confirmActionExecutions.value = actionExecutions;
        show.value = true;
    } else if (messages.length > 0) {
        // Everything the dry run reported is informational, so applying the refactoring would only
        // create an identical new workflow version. Say so rather than leaving the user with a
        // button that appears to do nothing.
        nothingToApply.value = true;
        confirmActionExecutions.value = actionExecutions;
        show.value = true;
    } else {
        executeRefactoring();
    }
}

async function executeRefactoring() {
    show.value = false;
    emit("onWorkflowMessage", "Applying requested workflow changes...", "progress");
    try {
        const data = await refactor(props.workflowId, props.refactorActions, "editor", false, props.version);
        emit("onRefactor", data);
    } catch (response) {
        onError(response as string);
    }
}
</script>

<template>
    <GModal
        :confirm="!nothingToApply"
        :show.sync="show"
        :title="nothingToApply ? 'Nothing to change' : title"
        :fixed-height="!nothingToApply"
        ok-text="Save"
        @ok="executeRefactoring">
        <div class="workflow-refactor-modal">
            {{ nothingToApply ? "This workflow is already up to date." : message }}
            <ul>
                <li v-for="(actionExecution, executionIndex) in confirmActionExecutions" :key="executionIndex">
                    <ul>
                        <li v-for="(actionMessage, messageIndex) in actionExecution.messages" :key="messageIndex">
                            - {{ actionMessage.message }}
                        </li>
                    </ul>
                </li>
            </ul>
        </div>
    </GModal>
</template>
