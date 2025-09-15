<script setup lang="ts">
import { faChevronDown, faChevronUp, faSignInAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { InvocationStep } from "@/api/invocations";
import type { WorkflowStepTyped } from "@/api/workflows";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { type GraphStep, statePlaceholders } from "@/composables/useInvocationGraph";

import ToolLinkPopover from "../Tool/ToolLinkPopover.vue";
import WorkflowStepIcon from "./WorkflowStepIcon.vue";
import WorkflowStepTitle from "./WorkflowStepTitle.vue";

interface Props {
    workflowStep: WorkflowStepTyped;
    graphStep?: GraphStep;
    invocationStep?: InvocationStep;
    canExpand?: boolean;
    expanded?: boolean;
}

const props = defineProps<Props>();

const stepLabel = computed(() => {
    const rawStepLabel = props.invocationStep?.workflow_step_label;
    if (rawStepLabel == null) {
        return undefined;
    }
    return rawStepLabel;
});
</script>

<template>
    <div class="d-flex justify-content-between">
        <div>
            <span :id="`step-icon-${props.workflowStep.id}`">
                <WorkflowStepIcon class="portlet-title-icon" :step-type="workflowStep.type" />
            </span>
            <ToolLinkPopover
                v-if="props.workflowStep.tool_id && props.workflowStep.tool_version"
                :target="`step-icon-${props.workflowStep.id}`"
                :tool-id="props.workflowStep.tool_id"
                :tool-version="props.workflowStep.tool_version" />
            <span class="portlet-title-text">
                <u class="step-title">
                    <WorkflowStepTitle
                        :step-index="props.workflowStep.id"
                        :step-label="stepLabel"
                        :step-type="props.workflowStep.type"
                        :step-tool-id="props.workflowStep.tool_id"
                        :step-tool-uuid="props.workflowStep.tool_uuid"
                        :step-subworkflow-id="
                            'workflow_id' in props.workflowStep ? props.workflowStep.workflow_id : null
                        " />
                </u>
            </span>
        </div>

        <span v-if="props.graphStep">
            <span v-if="isWorkflowInput(props.workflowStep.type)">
                <i>workflow input</i>
                <FontAwesomeIcon class="ml-1" :icon="faSignInAlt" />
            </span>
            <span v-else-if="props.graphStep.state">
                <i>{{ statePlaceholders[props.graphStep.state] || props.graphStep.state }}</i>
                <FontAwesomeIcon
                    v-if="props.graphStep.headerIcon"
                    class="ml-1"
                    :icon="props.graphStep.headerIcon"
                    :spin="props.graphStep.headerIconSpin" />
            </span>
            <FontAwesomeIcon v-if="props.canExpand" class="ml-1" :icon="props.expanded ? faChevronUp : faChevronDown" />
        </span>
    </div>
</template>
