<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { WorkflowRunModel } from "./model";
import { getRunData } from "./services";

import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowRunForm from "@/components/Workflow/Run/WorkflowRunForm.vue";
import WorkflowRunFormSimple from "@/components/Workflow/Run/WorkflowRunFormSimple.vue";
import WorkflowRunSuccess from "@/components/Workflow/Run/WorkflowRunSuccess.vue";

const historyStore = useHistoryStore();
const historyItemsStore = useHistoryItemsStore();
const { currentUser } = storeToRefs(useUserStore());

interface Props {
    workflowId: string;
    preferSimpleForm?: boolean;
    simpleFormTargetHistory?: string;
    simpleFormUseJobCache?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    preferSimpleForm: false,
    simpleFormTargetHistory: "current",
    simpleFormUseJobCache: false,
});

const formError = ref("");
const loading = ref(true);
const hasUpgradeMessages = ref(false);
const hasStepVersionChanges = ref(false);
const invocations = ref([]);
const simpleForm = ref(false);
const submissionError = ref("");
const workflowName = ref("");
const workflowModel: any = ref(null);

const currentHistoryId = computed(() => historyStore.currentHistoryId);
const editorLink = computed(() => `/workflows/edit?id=${props.workflowId}`);
const historyStatusKey = computed(() => `${currentHistoryId.value}_${lastUpdateTime.value}`);
const isOwner = computed(() => currentUser.value?.id === workflowModel.value.runData.id);
const lastUpdateTime = computed(() => historyItemsStore.lastUpdateTime);

function handleInvocations(incomingInvocations: any) {
    invocations.value = incomingInvocations;
    // make sure any new histories are added to historyStore
    invocations.value.forEach((invocation: any) => {
        historyStore.getHistoryById(invocation.history_id);
    });
}

function handleSubmissionError(error: string) {
    submissionError.value = errorMessageAsString(error);
}

function loadRun() {
    getRunData(props.workflowId)
        .then((runData) => {
            const incomingModel = new WorkflowRunModel(runData);
            simpleForm.value = props.preferSimpleForm;
            if (simpleForm.value) {
                // These only work with PJA - the API doesn't evaluate them at
                // all outside that context currently. The main workflow form renders
                // these dynamically and takes care of all the validation and setup details
                // on the frontend. If these are implemented on the backend at some
                // point this restriction can be lifted.
                if (incomingModel.hasReplacementParametersInToolForm) {
                    console.log("cannot render simple workflow form - has ${} values in tool steps");
                    simpleForm.value = false;
                }
                // If there are required parameters in a tool form (a disconnected runtime
                // input), we have to render the tool form steps and cannot use the
                // simplified tool form.
                if (incomingModel.hasOpenToolSteps) {
                    console.log(
                        "cannot render simple workflow form - one or more tools have disconnected runtime inputs"
                    );
                    simpleForm.value = false;
                }
                // Just render the whole form for resource request parameters (kind of
                // niche - I'm not sure anyone is using these currently anyway).
                if (incomingModel.hasWorkflowResourceParameters) {
                    console.log(`Cannot render simple workflow form - workflow resource parameters are configured`);
                    simpleForm.value = false;
                }
            }
            hasUpgradeMessages.value = incomingModel.hasUpgradeMessages;
            hasStepVersionChanges.value = incomingModel.hasStepVersionChanges;
            workflowName.value = incomingModel.name;
            workflowModel.value = incomingModel;
            loading.value = false;
        })
        .catch((response) => {
            formError.value = errorMessageAsString(response);
        });
}

function showAdvanced() {
    simpleForm.value = false;
}

onMounted(() => {
    loadRun();
});

watch(
    () => historyStatusKey.value,
    () => {
        if (invocations.value.length === 0) {
            loadRun();
        }
    }
);
</script>

<template>
    <span>
        <BAlert v-if="formError" variant="danger" show>
            <h2 class="h-text">Workflow cannot be executed. Please resolve the following issue:</h2>
            {{ formError }}
        </BAlert>
        <span v-else>
            <BAlert v-if="loading" variant="info" show>
                <LoadingSpan message="Loading workflow run data" />
            </BAlert>
            <WorkflowRunSuccess
                v-else-if="invocations.length > 0"
                :invocations="invocations"
                :workflow-name="workflowName" />
            <div v-else class="ui-form-composite">
                <BAlert v-if="!hasUpgradeMessages || hasStepVersionChanges" class="mb-4" variant="warning" show>
                    The <b>`{{ workflowName }}`</b> workflow may contain tools which have changed since it was last
                    saved or some error have been detected. Please
                    <RouterLink :to="editorLink">click here to edit and review the issues</RouterLink> before running
                    this workflow.
                </BAlert>
                <div v-else>
                    <BAlert v-if="submissionError" class="mb-4" variant="danger" show>
                        Workflow submission failed: {{ submissionError }}
                    </BAlert>
                    <WorkflowRunFormSimple
                        v-else-if="simpleForm"
                        :model="workflowModel"
                        :target-history="simpleFormTargetHistory"
                        :use-job-cache="simpleFormUseJobCache"
                        @submissionSuccess="handleInvocations"
                        @submissionError="handleSubmissionError"
                        @showAdvanced="showAdvanced" />
                    <WorkflowRunForm
                        v-else
                        :model="workflowModel"
                        @submissionSuccess="handleInvocations"
                        @submissionError="handleSubmissionError" />
                </div>
            </div>
        </span>
    </span>
</template>
