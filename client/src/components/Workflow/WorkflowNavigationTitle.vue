<script setup lang="ts">
import { faEdit, faSitemap, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import { isRegisteredUser } from "@/api";
import type { WorkflowInvocationElementView } from "@/api/invocations";
import type { WorkflowSummary } from "@/api/workflows";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { copyWorkflow } from "./workflows.services";

import AsyncButton from "../Common/AsyncButton.vue";
import ButtonSpinner from "../Common/ButtonSpinner.vue";
import LoadingSpan from "../LoadingSpan.vue";
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

const { workflow, loading, error } = useWorkflowInstance(props.workflowId);

const { currentUser, isAnonymous } = storeToRefs(useUserStore());
const owned = computed(() => {
    if (isRegisteredUser(currentUser.value) && workflow.value) {
        return currentUser.value.username === workflow.value.owner;
    } else {
        return false;
    }
});

const importErrorMessage = ref<string | null>(null);
const importedWorkflow = ref<WorkflowSummary | null>(null);
const workflowImportedAttempted = ref(false);

async function onImport() {
    if (!workflow.value || !workflow.value.owner) {
        return;
    }
    try {
        const wf = await copyWorkflow(workflow.value.id, workflow.value.owner);
        importedWorkflow.value = wf;
    } catch (error) {
        importErrorMessage.value = errorMessageAsString(error, "未能导入工作流");
    } finally {
        workflowImportedAttempted.value = true;
    }
}

function getWorkflowName(): string {
    return workflow.value?.name || "...";
}

const workflowImportTitle = computed(() => {
    if (isAnonymous.value) {
        return localize("登录以导入此工作流");
    } else if (workflowImportedAttempted.value) {
        return localize("工作流已导入");
    } else {
        return localize("导入此工作流");
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
                工作流 <b>{{ importedWorkflow.name }}</b> 导入成功。
            </span>
            <RouterLink to="/workflows/list">点击此处</RouterLink> 在工作流列表中查看已导入的工作流。
        </BAlert>

        <BAlert v-if="error" variant="danger" show>{{ error }}</BAlert>

        <div class="position-relative mb-2">
            <div v-if="workflow" class="bg-secondary px-2 py-1 rounded">
                <div class="d-flex align-items-center flex-gapx-1">
                    <div class="flex-grow-1" data-description="workflow heading">
                        <div>
                            <FontAwesomeIcon :icon="faSitemap" fixed-width />
                            <b> {{ props.invocation ? "已调用的" : "" }}工作流：{{ getWorkflowName() }} </b>
                            <span>(版本：{{ workflow.version + 1 }})</span>
                        </div>
                    </div>
                    <BButtonGroup>
                        <BButton
                            v-if="owned && workflow"
                            v-b-tooltip.hover.noninteractive.html
                            size="sm"
                            :title="
                                !workflow.deleted
                                    ? `<b>编辑</b><br>${getWorkflowName()}`
                                    : '此工作流已被删除。'
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
                        title="运行工作流"
                        @onClick="emit('on-execute')" />
                    <WorkflowRunButton
                        v-else
                        :id="workflow.id"
                        data-description="route to workflow run button"
                        variant="link"
                        :title="
                            !workflow.deleted
                                ? `<b>重新运行</b><br>${getWorkflowName()}`
                                : '此工作流已被删除。'
                        "
                        :disabled="workflow.deleted"
                        force
                        full
                        :version="workflow.version" />
                </div>
            </div>
            <div v-if="props.success" class="donemessagelarge">
                成功调用工作流
                <b>{{ getWorkflowName() }}</b>
            </div>
            <BAlert v-else-if="loading" variant="info" show>
                <LoadingSpan message="正在加载工作流详情" />
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
