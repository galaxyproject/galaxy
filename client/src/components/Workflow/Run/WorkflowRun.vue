<script setup lang="ts">
import { BAlert, BLink } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useRouter } from "vue-router/composables";

import { canMutateHistory } from "@/api";
import { getWorkflowInfo } from "@/api/workflows";
import { copyWorkflow } from "@/components/Workflow/workflows.services";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
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
const userStore = useUserStore();
const router = useRouter();

interface Props {
    workflowId: string;
    version?: string;
    preferSimpleForm?: boolean;
    simpleFormTargetHistory?: string;
    simpleFormUseJobCache?: boolean;
    requestState?: Record<string, never>;
    instance?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    version: undefined,
    preferSimpleForm: false,
    simpleFormTargetHistory: "current",
    simpleFormUseJobCache: false,
    requestState: undefined,
    instance: false,
});

const loading = ref(true);
const hasUpgradeMessages = ref(false);
const hasStepVersionChanges = ref(false);
const invocations = ref([]);
const simpleForm = ref(false);
const disableSimpleForm = ref(false);
const submissionError = ref("");
const workflowError = ref("");
const workflowName = ref("");
const workflowModel: any = ref(null);
const owner = ref<string>();

const currentHistoryId = computed(() => historyStore.currentHistoryId);
const editorLink = computed(
    () => `/workflows/edit?id=${props.workflowId}${props.version ? `&version=${props.version}` : ""}`
);
const historyStatusKey = computed(() => `${currentHistoryId.value}_${lastUpdateTime.value}`);
const isOwner = computed(() => userStore.matchesCurrentUsername(owner.value));
const lastUpdateTime = computed(() => historyItemsStore.lastUpdateTime);
const canRunOnHistory = computed(() => {
    if (!currentHistoryId.value) {
        return false;
    }
    const history = historyStore.getHistoryById(currentHistoryId.value);
    return (history && canMutateHistory(history)) ?? false;
});

if (props.instance) {
    const { workflow } = useWorkflowInstance(props.workflowId);
    watch(workflow, () => {
        if (workflow.value) {
            workflowName.value = workflow.value?.name;
            owner.value = workflow.value?.owner;
        }
    });
}

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

async function loadRun() {
    try {
        const runData = await getRunData(props.workflowId, props.version || undefined, props.instance);
        const incomingModel = new WorkflowRunModel(runData);

        simpleForm.value = props.preferSimpleForm;

        if (simpleForm.value) {
            // These only work with PJA - the API doesn't evaluate them at
            // all outside that context currently. The main workflow form renders
            // these dynamically and takes care of all the validation and setup details
            // on the frontend. If these are implemented on the backend at some
            // point this restriction can be lifted.
            if (incomingModel.hasReplacementParametersInToolForm) {
                console.log("无法渲染简化工作流表单 - 工具步骤中存在 ${} 值");
                simpleForm.value = false;
                disableSimpleForm.value = true;
            }
            // If there are required parameters in a tool form (a disconnected runtime
            // input), we have to render the tool form steps and cannot use the
            // simplified tool form.
            if (incomingModel.hasOpenToolSteps) {
                console.log("无法渲染简化工作流表单 - 一个或多个工具具有未连接的运行时输入");
                simpleForm.value = false;
                disableSimpleForm.value = true;
            }
            // Just render the whole form for resource request parameters (kind of
            // niche - I'm not sure anyone is using these currently anyway).
            if (incomingModel.hasWorkflowResourceParameters) {
                console.log(`无法渲染简化工作流表单 - 已配置工作流资源参数`);
                simpleForm.value = false;
                disableSimpleForm.value = true;
            }
        }

        hasUpgradeMessages.value = incomingModel.hasUpgradeMessages;
        hasStepVersionChanges.value = incomingModel.hasStepVersionChanges;
        workflowName.value = incomingModel.name;
        workflowModel.value = incomingModel;
        owner.value = incomingModel.runData.owner;
        loading.value = false;
    } catch (e) {
        const errMessage = errorMessageAsString(e);
        if (errMessage === "Workflow step has upgrade messages") {
            hasUpgradeMessages.value = true;
            if (!props.instance) {
                try {
                    const storedWorkflow = await getWorkflowInfo(props.workflowId);
                    owner.value = storedWorkflow.owner;
                    workflowName.value = storedWorkflow.name;
                } catch {
                    // just show original error
                    workflowError.value = errMessage;
                }
            }
        } else {
            workflowError.value = errMessage;
        }
        loading.value = false;
    }
}

async function onImport() {
    const response = await copyWorkflow(props.workflowId, owner.value, props.version);
    router.push(`/workflows/edit?id=${response.id}`);
}

const advancedForm = ref(false);
const fromVariant = computed<"simple" | "advanced">(() => {
    if (advancedForm.value) {
        return "advanced";
    } else if (simpleForm.value) {
        return "simple";
    } else {
        return "advanced";
    }
});

function showAdvanced() {
    advancedForm.value = true;
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

defineExpose({
    loading,
    simpleForm,
    submissionError,
    handleSubmissionError,
    workflowError,
    workflowModel,
});
</script>

<template>
    <span>
        <BAlert v-if="workflowError" variant="danger" show>
            <h2 class="h-text">工作流无法执行。请解决以下问题：</h2>
            {{ workflowError }}
        </BAlert>
        <span v-else>
            <BAlert v-if="loading" variant="info" show>
                <LoadingSpan message="正在加载工作流运行数据" />
            </BAlert>
            <WorkflowRunSuccess
                v-else-if="invocations.length > 0"
                :invocations="invocations"
                :workflow-name="workflowName" />
            <div v-else class="h-100">
                <BAlert
                    v-if="hasUpgradeMessages || hasStepVersionChanges"
                    class="mb-4"
                    variant="warning"
                    show
                    data-description="workflow run warning">
                    <span>
                        <b>`{{ workflowName }}`</b> 工作流可能包含自上次保存以来已更改的工具，或者检测到其他问题。请
                    </span>
                    <RouterLink v-if="isOwner" :to="editorLink">点击此处编辑并审查问题</RouterLink>
                    <BLink v-else @click="onImport">点击此处导入工作流并审查问题</BLink>
                    <span>，然后再运行此工作流。</span>
                </BAlert>
                <div v-else class="h-100">
                    <BAlert
                        v-if="submissionError"
                        class="mb-4"
                        variant="danger"
                        data-description="workflow run error"
                        show>
                        工作流提交失败：{{ submissionError }}
                    </BAlert>
                    <WorkflowRunFormSimple
                        v-if="fromVariant === 'simple'"
                        :model="workflowModel"
                        :target-history="simpleFormTargetHistory"
                        :use-job-cache="simpleFormUseJobCache"
                        :can-mutate-current-history="canRunOnHistory"
                        :request-state="requestState"
                        @submissionSuccess="handleInvocations"
                        @submissionError="handleSubmissionError"
                        @showAdvanced="showAdvanced" />
                    <WorkflowRunForm
                        v-else
                        :model="workflowModel"
                        :can-mutate-current-history="canRunOnHistory"
                        :disable-simple-form="disableSimpleForm"
                        @submissionSuccess="handleInvocations"
                        @submissionError="handleSubmissionError"
                        @showSimple="advancedForm = false" />
                </div>
            </div>
        </span>
    </span>
</template>
