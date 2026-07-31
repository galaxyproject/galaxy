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

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

interface Props {
    refactorActions: RefactorRequestAction[];
    versions: WorkflowVersion[];
    workflowId: string;
    version?: number;
    loading?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
    version: undefined,
    loading: false,
});

const emit = defineEmits<{
    (e: "onShow"): void;
    (e: "update:loading", loading: boolean): void;
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
        // emit that this is showing, so the workflow editor hides error modal.
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

    emit("update:loading", true);
    try {
        const data = await refactor(props.workflowId, props.refactorActions, "editor", true, props.version);
        await onDryRunResponse(data);
    } catch (response) {
        onError(response as string);
    } finally {
        emit("update:loading", false);
    }
}

function onError(response: string) {
    emit("onWorkflowError", "Reworking workflow failed...", response);
}

async function onDryRunResponse(data: RefactorResponse) {
    const actionExecutions = data.action_executions;
    const anyRequireConfirmation = actionExecutions.some((execution) => execution.messages.length > 0);
    if (anyRequireConfirmation) {
        confirmActionExecutions.value = actionExecutions;
        show.value = true;
    } else {
        await executeRefactoring();
    }
}

async function executeRefactoring() {
    show.value = false;
    emit("update:loading", true);
    try {
        const data = await refactor(props.workflowId, props.refactorActions, "editor", false, props.version);
        emit("onRefactor", data);
    } catch (response) {
        onError(response as string);
    } finally {
        emit("update:loading", false);
    }
}
</script>

<template>
    <GModal
        confirm
        :show.sync="show"
        title="Potential Issues Reworking Workflow"
        fixed-height
        ok-text="Proceed"
        @ok="executeRefactoring">
        <div class="workflow-refactor-modal">
            <GAlert>
                <div>The following issues were detected when attempting to rework this workflow.</div>
                <div>
                    Please review the messages below and click "Proceed" to continue with the rework, or "Cancel" to
                    abort.
                </div>
            </GAlert>
            <ol>
                <li v-for="(actionExecution, executionIndex) in confirmActionExecutions" :key="executionIndex">
                    <code>{{ actionExecution.action.action_type }}</code>
                    <span v-if="actionExecution.messages.length">:</span>
                    <ul>
                        <li v-for="(actionMessage, messageIndex) in actionExecution.messages" :key="messageIndex">
                            {{ actionMessage.message }}
                        </li>
                    </ul>
                </li>
            </ol>
        </div>
    </GModal>
</template>
