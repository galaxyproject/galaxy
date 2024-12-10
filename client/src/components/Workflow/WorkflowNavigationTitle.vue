<script setup lang="ts">
import { faEdit, faSitemap, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import { isRegisteredUser } from "@/api";
import type { WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useUserStore } from "@/stores/userStore";
import type { Workflow } from "@/stores/workflowStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { copyWorkflow } from "./workflows.services";

import AsyncButton from "../Common/AsyncButton.vue";
import ButtonSpinner from "../Common/ButtonSpinner.vue";
import WorkflowRunButton from "./WorkflowRunButton.vue";

interface Props {
    invocation?: WorkflowInvocationElementView;
    workflowId: string;
    runDisabled?: boolean;
    runWaiting?: boolean;
    success?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    invocation: undefined,
});

const emit = defineEmits<{
    (e: "on-execute"): void;
}>();

const { workflow, error } = useWorkflowInstance(props.workflowId);

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
const workflowImportedAttempted = ref(false);

async function onImport() {
    if (!workflow.value || !workflow.value.owner) {
        return;
    }
    try {
        const wf = await copyWorkflow(workflow.value.id, workflow.value.owner);
        importedWorkflow.value = wf as unknown as Workflow;
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
    } else {
        return localize("Import this workflow");
    }
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

        <BAlert v-if="error" variant="danger" show>{{ error }}</BAlert>

        <div class="position-relative mb-2">
            <div v-if="workflow" class="bg-secondary px-2 py-1 rounded">
                <div class="d-flex align-items-center flex-gapx-1">
                    <div class="flex-grow-1" data-description="workflow heading">
                        <div>
                            <FontAwesomeIcon :icon="faSitemap" fixed-width />
                            <b> {{ props.invocation ? "Invoked " : "" }}Workflow: {{ getWorkflowName() }} </b>
                            <span>(Version: {{ workflow.version + 1 }})</span>
                        </div>
                    </div>
                    <BButtonGroup>
                        <BButton
                            v-if="owned && workflow"
                            v-b-tooltip.hover.noninteractive.html
                            size="sm"
                            :title="
                                !workflow.deleted
                                    ? `<b>Edit</b><br>${getWorkflowName()}`
                                    : 'This workflow has been deleted.'
                            "
                            variant="link"
                            :disabled="workflow.deleted"
                            :to="`/workflows/edit?id=${workflow.id}&version=${workflow.version}`">
                            <FontAwesomeIcon :icon="faEdit" fixed-width />
                        </BButton>
                        <AsyncButton
                            v-else
                            v-b-tooltip.hover.noninteractive
                            data-description="import workflow button"
                            size="sm"
                            :disabled="isAnonymous || workflowImportedAttempted"
                            :title="workflowImportTitle"
                            :icon="faUpload"
                            variant="link"
                            :action="onImport">
                        </AsyncButton>

                        <slot name="workflow-title-actions" />
                    </BButtonGroup>
                    <ButtonSpinner
                        v-if="!props.invocation"
                        id="run-workflow"
                        data-description="execute workflow button"
                        :wait="runWaiting"
                        :disabled="runDisabled"
                        size="sm"
                        title="Run Workflow"
                        @onClick="emit('on-execute')" />
                    <WorkflowRunButton
                        v-else
                        :id="workflow.id"
                        data-description="route to workflow run button"
                        variant="link"
                        :title="
                            !workflow.deleted
                                ? `<b>Rerun</b><br>${getWorkflowName()}`
                                : 'This workflow has been deleted.'
                        "
                        :disabled="workflow.deleted"
                        force
                        full
                        :version="workflow.version" />
                </div>
            </div>
            <div v-if="props.success" class="donemessagelarge">
                Successfully invoked workflow
                <b>{{ getWorkflowName() }}</b>
            </div>
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
