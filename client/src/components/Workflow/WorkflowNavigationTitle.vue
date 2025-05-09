<script setup lang="ts">
import { faEdit, faPlay, faRedo, faSitemap, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";
import { useRouter } from "vue-router/composables";

import type { WorkflowInvocationElementView } from "@/api/invocations";
import type { WorkflowSummary } from "@/api/workflows";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { copyWorkflow } from "./workflows.services";

import GButton from "../BaseComponents/GButton.vue";
import GButtonGroup from "../BaseComponents/GButtonGroup.vue";
import AsyncButton from "../Common/AsyncButton.vue";
import ButtonSpinner from "../Common/ButtonSpinner.vue";
import LoadingSpan from "../LoadingSpan.vue";

const router = useRouter();

interface Props {
    invocation?: WorkflowInvocationElementView;
    workflowId: string;
    runDisabled?: boolean;
    runWaiting?: boolean;
    success?: boolean;
    validRerun?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    invocation: undefined,
});

const emit = defineEmits<{
    (e: "on-execute"): void;
}>();

const { workflow, loading, error, owned } = useWorkflowInstance(props.workflowId);

const { isAnonymous } = storeToRefs(useUserStore());

const importErrorMessage = ref<string | null>(null);
const importedWorkflow = ref<WorkflowSummary | null>(null);
const workflowImportedAttempted = ref(false);

const { confirm } = useConfirmDialog();

async function onImport() {
    if (!workflow.value || !workflow.value.owner) {
        return;
    }
    try {
        const wf = await copyWorkflow(workflow.value.id, workflow.value.owner);
        importedWorkflow.value = wf;
    } catch (error) {
        importErrorMessage.value = errorMessageAsString(error, "Failed to import workflow");
    } finally {
        workflowImportedAttempted.value = true;
    }
}

function getWorkflowName(): string {
    return workflow.value?.name || "...";
}

const workflowImportTitle = computed(() => {
    if (isAnonymous.value) {
        return localize("Login to import this workflow");
    } else if (workflowImportedAttempted.value) {
        return localize("Workflow imported");
    } else if (workflow.value?.deleted) {
        return localize("This workflow has been deleted");
    } else {
        return localize("Import this workflow");
    }
});

const executeButtonTooltip = computed(() => {
    if (props.runDisabled) {
        return localize("Fix the errors in the workflow before running it");
    } else if (props.validRerun) {
        return localize("Rerun this workflow with the original inputs");
    } else {
        return localize("Execute this workflow");
    }
});

const { currentHistoryId } = storeToRefs(useHistoryStore());

async function rerunWorkflow() {
    if (!props.invocation) {
        return;
    }
    if (props.invocation.history_id === currentHistoryId.value) {
        router.push(`/workflows/rerun?invocation_id=${props.invocation.id}`);
        return;
    }
    const confirmed = await confirm(
        localize(
            "Rerunning this workflow requires changing the history to the one with the original inputs. Do you want to continue?"
        ),
        {
            id: "change-history-rerun-workflow",
            title: localize("Change History and Rerun Workflow"),
            okTitle: localize("Change History and Rerun"),
            okVariant: "primary",
        }
    );

    if (confirmed) {
        router.push(`/workflows/rerun?invocation_id=${props.invocation.id}`);
    }
}
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

        <BAlert v-if="error" variant="danger" show>{{ error }}</BAlert>

        <div class="position-relative">
            <div v-if="workflow" class="bg-secondary px-2 py-1 rounded">
                <div class="d-flex align-items-center flex-gapx-1">
                    <div class="flex-grow-1" data-description="workflow heading">
                        <div>
                            <FontAwesomeIcon :icon="faSitemap" fixed-width />
                            <b> {{ props.invocation ? "Invoked " : "" }}Workflow: {{ getWorkflowName() }} </b>
                            <span>(Version: {{ workflow.version + 1 }})</span>
                        </div>
                    </div>
                    <GButtonGroup data-button-group>
                        <GButton
                            v-if="owned && workflow"
                            tooltip
                            data-button-edit
                            transparent
                            color="blue"
                            size="small"
                            title="Edit Workflow"
                            disabled-title="This workflow has been deleted."
                            :disabled="workflow.deleted"
                            :to="`/workflows/edit?id=${workflow.id}&version=${workflow.version}`">
                            <FontAwesomeIcon :icon="faEdit" fixed-width />
                        </GButton>
                        <AsyncButton
                            v-else
                            data-description="import workflow button"
                            transparent
                            color="blue"
                            size="small"
                            :disabled="isAnonymous || workflowImportedAttempted"
                            :title="workflowImportTitle"
                            :icon="faUpload"
                            :action="onImport">
                        </AsyncButton>

                        <slot name="workflow-title-actions" />
                    </GButtonGroup>
                    <ButtonSpinner
                        v-if="!props.invocation"
                        id="run-workflow"
                        data-description="execute workflow button"
                        :wait="runWaiting"
                        :disabled="runDisabled"
                        size="small"
                        :tooltip="executeButtonTooltip"
                        :title="!props.validRerun ? 'Run Workflow' : 'Rerun Workflow'"
                        @onClick="emit('on-execute')" />
                    <GButtonGroup v-else>
                        <GButton
                            title="Run Workflow"
                            disabled-title="This workflow has been deleted."
                            data-button-run
                            tooltip
                            color="blue"
                            size="small"
                            :disabled="workflow.deleted"
                            :to="`/workflows/run?id=${workflow.id}&version=${workflow.version}`">
                            <FontAwesomeIcon :icon="faPlay" fixed-width />
                            <span v-localize>Run</span>
                        </GButton>
                        <GButton
                            title="Rerun Workflow with same inputs"
                            disabled-title="This workflow has been deleted."
                            data-button-rerun
                            tooltip
                            color="blue"
                            size="small"
                            :disabled="workflow.deleted"
                            @click="rerunWorkflow">
                            <FontAwesomeIcon :icon="faRedo" fixed-width />
                            <span v-localize>Rerun</span>
                        </GButton>
                    </GButtonGroup>
                </div>
            </div>
            <div v-if="props.success" class="donemessagelarge">
                Successfully invoked workflow
                <b>{{ getWorkflowName() }}</b>
            </div>
            <BAlert v-else-if="loading" variant="info" show>
                <LoadingSpan message="Loading workflow details" />
            </BAlert>
        </div>
    </div>
</template>

<style scoped lang="scss">
@keyframes fadeOut {
    0% {
        opacity: 1;
    }
    100% {
        opacity: 0;
        display: none;
        pointer-events: none;
    }
}

.donemessagelarge {
    top: 0;
    position: absolute;
    width: 100%;
    animation: fadeOut 3s forwards;
}
</style>
