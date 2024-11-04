<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faArrowLeft, faChevronDown, faChevronUp,faEdit, faHdd, faSitemap, faUpload  } from "@fortawesome/free-solid-svg-icons";
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
    workflowId: string;
    updateTime: string;
    historyId: string;
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

const { workflow } = useWorkflowInstance(props.workflowId);

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
    //TODO move onExecute() from *FormSimple.vue to here
}
</script>

<template>
    <div class="py-2 pl-3 d-flex justify-content-between align-items-center">
        <div v-if="props.workflowId">
            <i>
                <FontAwesomeIcon :icon="faClock" class="mr-1" />invoked
                <UtcDate :date="props.updateTime" mode="elapsed" />
            </i>
            <span class="d-flex flex-gapx-1 align-items-center">
                <FontAwesomeIcon :icon="faHdd" />History:
                <!-- TODO uncomment for *FormSimple.vue -->
                <SwitchToHistoryLink :history-id="props.historyId" />
            </span>
        </div>
        <div v-if="workflow" class="d-flex flex-gapx-1 align-items-center">
            <div class="d-flex flex-column align-items-end mr-2">
                <WorkflowIndicators
                    :workflow="workflow"
                    :published-view="true"
                    @update-filter="(k, v) => emit('update-filter', k, v)" />
                <!-- <WorkflowIndicators
                    :workflow="workflow"
                    :published-view="publishedView"
                    @update-filter="(k, v) => emit('update-filter', k, v)" /> -->
                <WorkflowInvocationsCount class="float-right" :workflow="workflow" />
            </div>
        </div>
    </div>
</template>
