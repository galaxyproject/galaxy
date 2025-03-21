<script setup lang="ts">
import { computed } from "vue";

import type { InvocationMessage } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";

import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";
import JobInformation from "@/components/JobInformation/JobInformation.vue";
import WorkflowInvocationStep from "@/components/WorkflowInvocationState/WorkflowInvocationStep.vue";

type ReasonToLevel = {
    history_deleted: "cancel";
    user_request: "cancel";
    cancelled_on_review: "cancel";
    dataset_failed: "error";
    collection_failed: "error";
    job_failed: "error";
    output_not_found: "error";
    expression_evaluation_failed: "error";
    when_not_boolean: "error";
    unexpected_failure: "error";
    workflow_output_not_found: "warning";
    workflow_parameter_invalid: "error";
};

const level: ReasonToLevel = {
    history_deleted: "cancel",
    user_request: "cancel",
    cancelled_on_review: "cancel",
    dataset_failed: "error",
    collection_failed: "error",
    job_failed: "error",
    output_not_found: "error",
    expression_evaluation_failed: "error",
    when_not_boolean: "error",
    unexpected_failure: "error",
    workflow_output_not_found: "warning",
    workflow_parameter_invalid: "error",
};

const levelClasses = {
    warning: "warningmessage",
    cancel: "infomessage",
    error: "errormessage",
};

interface Invocation {
    workflow_id: string;
    state: string;
}

interface InvocationMessageProps {
    invocationMessage: InvocationMessage;
    invocation: Invocation;
}

const props = defineProps<InvocationMessageProps>();
const levelClass = computed(() => levelClasses[level[props.invocationMessage.reason]]);

const workflow = computed(() => {
    if ("workflow_step_id" in props.invocationMessage) {
        const { workflow } = useWorkflowInstance(props.invocation.workflow_id);
        return workflow.value;
    }
    return undefined;
});

const workflowStep = computed(() => {
    if (
        "workflow_step_id" in props.invocationMessage &&
        props.invocationMessage.workflow_step_id !== undefined &&
        props.invocationMessage.workflow_step_id !== null &&
        workflow.value
    ) {
        return workflow.value.steps[props.invocationMessage.workflow_step_id];
    }
    return undefined;
});

const dependentWorkflowStep = computed(() => {
    if ("dependent_workflow_step_id" in props.invocationMessage && workflow.value) {
        const stepId = props.invocationMessage["dependent_workflow_step_id"];
        if (stepId !== undefined && stepId !== null) {
            return workflow.value.steps[stepId];
        }
    }
    return undefined;
});

const jobId = computed(() => "job_id" in props.invocationMessage && props.invocationMessage.job_id);
const HdaId = computed(() => "hda_id" in props.invocationMessage && props.invocationMessage.hda_id);
const HdcaId = computed(() => "hdca_id" in props.invocationMessage && props.invocationMessage.hdca_id);

const cancelFragment = "工作流调用安排已取消，因为";
const failFragment = "工作流调用安排失败，因为 ";
const stepDescription = computed(() => {
    const messageLevel = level[props.invocationMessage.reason];
    if (messageLevel === "warning") {
        return "此步骤引发了一个警告";
    } else if (messageLevel === "cancel") {
        return "此步骤取消了调用";
    } else if (messageLevel === "error") {
        return "此步骤导致调用失败";
    } else {
        throw Error("未知的消息级别");
    }
});

const infoString = computed(() => {
    const invocationMessage = props.invocationMessage;
    const reason = invocationMessage.reason;
    if (reason === "user_request") {
        return `${cancelFragment} 用户请求取消。`;
    } else if (reason === "history_deleted") {
        return `${cancelFragment} 调用的历史记录已被删除。`;
    } else if (reason === "cancelled_on_review") {
        return `${cancelFragment} 工作流在步骤 ${
            invocationMessage.workflow_step_id + 1
        } 被暂停，未被批准。`;
    } else if (reason === "collection_failed") {
        return `${failFragment} 步骤 ${
            invocationMessage.workflow_step_id + 1
        } 需要步骤 ${
            invocationMessage.dependent_workflow_step_id + 1
        } 创建的数据集集合，但数据集集合进入了失败状态。`;
    } else if (reason === "dataset_failed") {
        if (
            invocationMessage.dependent_workflow_step_id !== null &&
            invocationMessage.dependent_workflow_step_id !== undefined
        ) {
            return `${failFragment} 步骤 ${invocationMessage.workflow_step_id + 1} 需要步骤 ${
                invocationMessage.dependent_workflow_step_id + 1
            } 创建的数据集，但数据集进入了失败状态。`;
        } else {
            return `${failFragment} 步骤 ${
                invocationMessage.workflow_step_id + 1
            } 需要一个数据集，但数据集进入了失败状态。`;
        }
    } else if (reason === "job_failed") {
        return `${failFragment} 步骤 ${invocationMessage.workflow_step_id + 1} 依赖于在步骤 ${
            invocationMessage.dependent_workflow_step_id + 1
        } 中创建的作业，但该步骤的作业失败了。`;
    } else if (reason === "output_not_found") {
        return `${failFragment} 步骤 ${invocationMessage.workflow_step_id + 1} 依赖于步骤 ${
            invocationMessage.dependent_workflow_step_id + 1
        } 的输出 '${invocationMessage.output_name}'，但该步骤没有生成该名称的输出。`;
    } else if (reason === "expression_evaluation_failed") {
        return `${failFragment} 步骤 ${
            invocationMessage.workflow_step_id + 1
        } 包含无法计算的表达式。`;
    } else if (reason === "when_not_boolean") {
        return `${failFragment} 步骤 ${
            invocationMessage.workflow_step_id + 1
        } 是一个条件步骤，且 when 表达式的结果不是布尔类型。`;
    } else if (reason === "unexpected_failure") {
        let atStep = "";
        if (invocationMessage.workflow_step_id !== null && invocationMessage.workflow_step_id !== undefined) {
            atStep = ` 在步骤 ${invocationMessage.workflow_step_id + 1}`;
        }
        if (invocationMessage.details) {
            return `${failFragment} 发生了一个意外失败${atStep}: '${invocationMessage.details}'`;
        }
        return `${failFragment} 发生了一个意外失败${atStep}。`;
    } else if (reason === "workflow_output_not_found") {
        return `定义的工作流输出 '${invocationMessage.output_name}' 在步骤 ${
            invocationMessage.workflow_step_id + 1
        } 中未找到。`;
    } else if (reason === "workflow_parameter_invalid") {
        return `步骤 ${invocationMessage.workflow_step_id + 1} 的工作流参数未通过验证: ${
            invocationMessage.details
        }`;
    } else {
        return reason;
    }
});
</script>

<template>
    <div>
        <div :class="levelClass" style="text-align: center">
            {{ infoString }}
        </div>
        <div v-if="dependentWorkflowStep">
            此步骤出现问题：
            <WorkflowInvocationStep
                :invocation="invocation"
                :workflow="workflow"
                :workflow-step="dependentWorkflowStep"></WorkflowInvocationStep>
        </div>
        <div v-if="workflowStep">
            {{ stepDescription }}
            <WorkflowInvocationStep
                :invocation="invocation"
                :workflow="workflow"
                :workflow-step="workflowStep"></WorkflowInvocationStep>
        </div>
        <div v-if="HdaId">
            此数据集失败：
            <GenericHistoryItem :item-id="HdaId" item-src="hda" />
        </div>
        <div v-if="HdcaId">
            此数据集集合失败：
            <GenericHistoryItem :item-id="HdcaId" item-src="hdca" />
        </div>
        <div v-if="jobId">
            此任务失败：
            <JobInformation :job_id="jobId" />
        </div>
    </div>
</template>