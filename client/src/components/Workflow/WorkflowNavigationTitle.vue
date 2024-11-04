<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faArrowLeft, faChevronDown, faChevronUp,faEdit, faSitemap, faUpload  } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import { isRegisteredUser } from "@/api";
import type { WorkflowInvocationElementView } from "@/api/invocations";
import { useConfig } from "@/composables/config";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useUserStore } from "@/stores/userStore";
import type { Workflow } from "@/stores/workflowStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { allowCachedJobs } from "../Tool/utilities";
import { copyWorkflow } from "./workflows.services";

import AsyncButton from "../Common/AsyncButton.vue";
import ButtonSpinner from "../Common/ButtonSpinner.vue";
import Heading from "../Common/Heading.vue";
import SwitchToHistoryLink from "../History/SwitchToHistoryLink.vue";
import UtcDate from "../UtcDate.vue";
import WorkflowInvocationsCount from "../Workflow/WorkflowInvocationsCount.vue";
import WorkflowRunButton from "../Workflow/WorkflowRunButton.vue";
import WorkflowIndicators from "@/components/Workflow/List/WorkflowIndicators.vue";

library.add(faChevronDown, faChevronUp);

interface Props {
    invocation: WorkflowInvocationElementView;
    fromPanel?: boolean;
    targetHistory?: string;
    useJobCache?: boolean;
    canMutateCurrentHistory?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    // index: undefined,
    // isSubworkflow: false,
    targetHistory: "current",
    useJobCache: false,
    canMutateCurrentHistory: false,
});

const emit = defineEmits<{
    (e: "update-filter", key: string, value: any): void;
}>();

// const props = defineProps<Props>();
const newHistory = props.targetHistory == "new" || props.targetHistory == "prefer_new";
const useCachedJobs = ref(props.useJobCache);

const { workflow } = useWorkflowInstance(props.invocation.workflow_id);

const expandAnnotations = ref(true);

const { currentUser, isAnonymous } = storeToRefs(useUserStore());
const owned = computed(() => {
    if (isRegisteredUser(currentUser.value) && workflow.value) {
        return currentUser.value.username === workflow.value.owner;
    } else {
        return false;
    }
});
const hasValidationErrors = computed(() => {
    return Boolean(Object.values(stepValidations).find((value) => value !== null && value !== undefined));
});
const canRunOnHistory = computed(() => {
    return props.canMutateCurrentHistory || sendToNewHistory;
})

const importErrorMessage = ref<string | null>(null);
const importedWorkflow = ref<Workflow | null>(null);
const { config, isConfigLoaded } = useConfig(true);
const splitObjectStore = ref(false);
const preferredObjectStoreId = ref<string | null>(null);
const preferredIntermediateObjectStoreId = ref<string | null>(null);
const waitingForRequest = ref(false);
const stepValidations = ref({});
const sendToNewHistory = ref(newHistory);

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

function reuseAllowed(user: any) {
    return user && allowCachedJobs(user.preferences);
}

function showRuntimeSettings(user: any) {
    return props.targetHistory.indexOf("prefer") >= 0 || (user && reuseAllowed(user));
}

function onStorageUpdate (objectStoreId: any, intermediate: any) {
    if (intermediate) {
        preferredIntermediateObjectStoreId.value = objectStoreId;
    } else {
        preferredObjectStoreId.value = objectStoreId;
    }
}

function onExecute() {
    //TODO refactor onExecute() from *FormSimple.vue to here
}
</script>

<template>
    <div>
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

        <div class="ui-portlet-section">
            <div class="d-flex portlet-header">
                <div class="flex-grow-1">
                    <div class="px-1">
                        <span class="fa fa-sitemap" />
                        <b class="mx-1">{{ props.invocation ? "Invoked ": "" }}Workflow: {{ getWorkflowName() }}</b>
                        <i v-if="workflow">(version: {{ workflow.version + 1 }})</i>
                    </div>
                </div>
                <div class="d-flex align-items-end flex-nowrap">
                    <BButton
                        v-if="!props.fromPanel"
                        v-b-tooltip.hover.bottom.noninteractive
                        aria-haspopup="true"
                        class="search-clear"
                        size="md"
                        :title="localize('Return to Invocations List')"
                        variant="link"
                        data-description="reset query"
                        @click="$router.push(`/workflows/invocations`)">
                        <span class="fa fa-list" />
                    </BButton>
                    <b-dropdown
                        v-if="showRuntimeSettings(currentUser)"
                        id="dropdown-form"
                        ref="dropdown"
                        class="workflow-run-settings"
                        title="Workflow Run Settings"
                        variant="link"
                        no-caret>
                        <template v-slot:button-content>
                            <span class="fa fa-cog" />
                        </template>
                        <b-dropdown-form>
                            <b-form-checkbox v-model="sendToNewHistory" class="workflow-run-settings-target">
                                Send results to a new history
                            </b-form-checkbox>
                            <b-form-checkbox
                                v-if="reuseAllowed(currentUser)"
                                v-model="useCachedJobs"
                                title="This may skip executing jobs that you have already run.">
                                Attempt to re-use jobs with identical parameters?
                            </b-form-checkbox>
                            <b-form-checkbox
                                v-if="isConfigLoaded && config.object_store_allows_id_selection"
                                v-model="splitObjectStore">
                                Send outputs and intermediate to different storage locations?
                            </b-form-checkbox>
                            <WorkflowStorageConfiguration
                                v-if="isConfigLoaded && config.object_store_allows_id_selection"
                                :split-object-store="splitObjectStore"
                                :invocation-preferred-object-store-id="preferredObjectStoreId"
                                :invocation-intermediate-preferred-object-store-id="
                                    preferredIntermediateObjectStoreId
                                "
                                @updated="onStorageUpdate">
                            </WorkflowStorageConfiguration>
                        </b-dropdown-form>
                    </b-dropdown>
                    <BButton
                        v-if="owned && workflow"
                        v-b-tooltip.hover.noninteractive.html
                        size="md"
                        class="search-clear"
                        :title="
                            !workflow.deleted
                                ? `Edit ${getWorkflowName()}`
                                : 'This workflow has been deleted.'
                        "
                        variant="link"
                        :disabled="workflow.deleted"
                        @click="$router.push(`/workflows/edit?id=${workflow.id}&version=${workflow.version}`)">
                        <span class="fa fa-edit" />
                    </BButton>
                    <AsyncButton
                        v-else
                        v-b-tooltip.hover.noninteractive
                        size="md"
                        :disabled="isAnonymous"
                        :title="localize('Import this workflow')"
                        :icon="faUpload"
                        variant="secondary"
                        :action="onImport">
                    </AsyncButton>
                    <ButtonSpinner
                        id="run-workflow"
                        :wait="waitingForRequest"
                        :disabled="hasValidationErrors || !canRunOnHistory"
                        title="Run"
                        @onClick="onExecute" />
                </div>
            </div>
        </div>
    </div>
    </div>
</template>
