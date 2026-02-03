<script setup lang="ts">
import { ref, watch } from "vue";

import {
    refactor,
    type RefactorRequestAction,
    type RefactorResponse,
    type RefactorResponseActionExecution,
} from "@/api/workflows";

import GModal from "@/components/BaseComponents/GModal.vue";

interface Props {
    refactorActions: RefactorRequestAction[];
    workflowId: string;
    title?: string;
    message?: string;
}
const props = withDefaults(defineProps<Props>(), {
    title: "Issues reworking this workflow",
    message: "Please review the following potential issues...",
});

const emit = defineEmits<{
    (e: "onShow"): void;
    (e: "onWorkflowMessage", message: string, type: string): void;
    (e: "onWorkflowError", message: string, response: any): void;
    (e: "onRefactor", data: RefactorResponse): void;
}>();

const show = ref(props.refactorActions.length > 0);
const confirmActionExecutions = ref<RefactorResponseActionExecution[]>([]);

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
    emit("onWorkflowMessage", "Pre-checking requested workflow changes (dry run)...", "progress");
    try {
        const data = await refactor(props.workflowId, props.refactorActions, "editor", true);
        onDryRunResponse(data);
    } catch (response) {
        onError(response as string);
    }
}

function onError(response: string) {
    emit("onWorkflowError", "Reworking workflow failed...", response);
}

function onDryRunResponse(data: RefactorResponse) {
    // TODO: type from schema
    const actionExecutions = data.action_executions;
    const anyRequireConfirmation = actionExecutions.some(
        (execution: RefactorResponseActionExecution) => execution.messages.length > 0,
    );
    if (anyRequireConfirmation) {
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
        const data = await refactor(props.workflowId, props.refactorActions, "editor", false);
        emit("onRefactor", data);
    } catch (response) {
        onError(response as string);
    }
}
</script>

<template>
    <GModal :show.sync="show" :title="title" fixed-height ok-text="Save" @ok="executeRefactoring">
        <div class="workflow-refactor-modal">
            {{ message }}
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
