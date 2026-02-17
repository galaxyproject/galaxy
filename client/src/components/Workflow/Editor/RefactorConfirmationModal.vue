<script setup lang="ts">
import { computed, ref, watch } from "vue";

import {
    refactor,
    type RefactorRequestAction,
    type RefactorResponse,
    type RefactorResponseActionExecution,
    type WorkflowVersion,
} from "@/api/workflows";
import { useConfirmDialog } from "@/composables/confirmDialog";

import GModal from "@/components/BaseComponents/GModal.vue";

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
                okTitle: `Yes, refactor "Version ${props.version! + 1}"`,
                cancelTitle: "No, cancel refactor",
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
        const data = await refactor(props.workflowId, props.refactorActions, "editor", false, props.version);
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
