<script setup lang="ts">
import { faChevronDown, faChevronUp, faSignInAlt, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { computed } from "vue";

import type { InvocationStep } from "@/api/invocations";
import type { WorkflowStepTyped } from "@/api/workflows";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { type GraphStep, statePlaceholders } from "@/composables/useInvocationGraph";
import { useUid } from "@/composables/utils/uid";
import { useInvocationStore } from "@/stores/invocationStore";

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

const invocationStore = useInvocationStore();

/** Per-instance id, since the same step header can render twice (step card and expanded modal) */
const stepIconId = useUid("step-icon-");

const isPolling = computed(() =>
    props.invocationStep ? invocationStore.isLoadingInvocationStep(props.invocationStep.id) : false,
);
</script>

<template>
    <div class="d-flex justify-content-between align-items-center w-100">
        <div>
            <span :id="stepIconId">
                <WorkflowStepIcon class="portlet-title-icon" :step-type="workflowStep.type" />
            </span>
            <ToolLinkPopover
                v-if="props.workflowStep.tool_id && props.workflowStep.tool_version"
                :target="stepIconId"
                :tool-id="props.workflowStep.tool_id"
                :tool-version="props.workflowStep.tool_version" />
            <span class="portlet-title-text">
                <u class="step-title">
                    <WorkflowStepTitle :invocation-step="props.invocationStep" :workflow-step="props.workflowStep" />
                </u>
            </span>
        </div>

        <span v-if="props.graphStep" class="text-nowrap">
            <BBadge v-if="isPolling" v-g-tooltip.hover class="mr-1" title="Polling for updates" variant="link">
                <FontAwesomeIcon :icon="faSpinner" spin />
            </BBadge>

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
