<script setup lang="ts">
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { InvocationMessage, WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

import { INVOCATION_MSG_LEVEL } from "./util";

import GCard from "../Common/GCard.vue";
import InvocationMessageView from "./InvocationMessage.vue";
import WorkflowStepTitle from "./WorkflowStepTitle.vue";
import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";

interface InvocationMessageProps {
    invocationMessage: InvocationMessage;
    invocation: WorkflowInvocationElementView;
    storeId: string;
}

const props = defineProps<InvocationMessageProps>();

const emit = defineEmits<{
    (e: "view-step", stepId: number): void;
}>();

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
const invocationStep = computed(() => {
    if (workflowStep.value) {
        return props.invocation.steps[workflowStep.value.id];
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
const dependentInvocationStep = computed(() => {
    if (dependentWorkflowStep.value) {
        return props.invocation.steps[dependentWorkflowStep.value.id];
    }
    return undefined;
});

// This is used to indicate on the step cards whether the step is currently active in the invocation graph.\
const { activeNodeId } = storeToRefs(useWorkflowStateStore(props.storeId));

const jobId = computed(() => "job_id" in props.invocationMessage && props.invocationMessage.job_id);
const HdaId = computed(() => "hda_id" in props.invocationMessage && props.invocationMessage.hda_id);
const HdcaId = computed(() => "hdca_id" in props.invocationMessage && props.invocationMessage.hdca_id);

const stepDescription = computed(() => {
    const messageLevel = INVOCATION_MSG_LEVEL[props.invocationMessage.reason];
    if (messageLevel === "warning") {
        return "This step caused a warning";
    } else if (messageLevel === "cancel") {
        return "This step canceled the invocation";
    } else if (messageLevel === "error") {
        return "This step failed the invocation";
    } else {
        throw Error("Unknown message level");
    }
});

function openJobInNewTab(jobId: string) {
    const url = `/jobs/${jobId}/view`;
    window.open(url, "_blank");
}
</script>

<template>
    <div>
        <InvocationMessageView :invocation-message="props.invocationMessage" />
        <div class="invocation-error-grid d-flex flex-wrap">
            <GCard
                v-if="dependentWorkflowStep"
                clickable
                :current="activeNodeId === dependentWorkflowStep.id"
                grid-view
                @click="emit('view-step', dependentWorkflowStep.id)">
                Problem occurred at this step:
                <strong>
                    <WorkflowStepTitle
                        :step-index="dependentWorkflowStep.id"
                        :step-label="
                            dependentInvocationStep?.workflow_step_label || `Step ${dependentWorkflowStep.id + 1}`
                        "
                        :step-type="dependentWorkflowStep.type"
                        :step-tool-id="dependentWorkflowStep.tool_id"
                        :step-subworkflow-id="
                            'workflow_id' in dependentWorkflowStep ? dependentWorkflowStep.workflow_id : null
                        " />
                </strong>
            </GCard>
            <GCard
                v-if="workflowStep"
                clickable
                :current="activeNodeId === workflowStep.id"
                grid-view
                @click="emit('view-step', workflowStep.id)">
                {{ stepDescription }}:
                <strong>
                    <WorkflowStepTitle
                        :step-index="workflowStep.id"
                        :step-label="invocationStep?.workflow_step_label || `Step ${workflowStep.id + 1}`"
                        :step-type="workflowStep.type"
                        :step-tool-id="workflowStep.tool_id"
                        :step-subworkflow-id="'workflow_id' in workflowStep ? workflowStep.workflow_id : null" />
                </strong>
            </GCard>
            <GCard v-if="HdaId" grid-view>
                This dataset failed:
                <GenericHistoryItem :item-id="HdaId" item-src="hda" />
            </GCard>
            <GCard v-if="HdcaId" grid-view>
                This dataset collection failed:
                <GenericHistoryItem :item-id="HdcaId" item-src="hdca" />
            </GCard>
            <GCard v-if="jobId" clickable grid-view @click="openJobInNewTab(jobId)">
                <span>
                    This job failed: <strong> {{ jobId }} </strong>
                </span>
                <i>
                    Click to view job details in a new tab
                    <FontAwesomeIcon :icon="faExternalLinkAlt" />
                </i>
            </GCard>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "_breakpoints.scss";

.invocation-error-grid {
    container: cards-list / inline-size;
}
</style>
