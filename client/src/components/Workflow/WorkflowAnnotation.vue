<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { useWorkflowInstance } from "@/composables/useWorkflowInstance";

import TextSummary from "../Common/TextSummary.vue";
import TargetHistoryLink from "../History/TargetHistoryLink.vue";
import StatelessTags from "../TagsMultiselect/StatelessTags.vue";
import UtcDate from "../UtcDate.vue";
import WorkflowInvocationsCount from "../Workflow/WorkflowInvocationsCount.vue";
import WorkflowIndicators from "@/components/Workflow/List/WorkflowIndicators.vue";

interface Props {
    workflowId: string;
    /** The time the workflow run was invoked. This prop being set also
     * decides that this is being rendered in the invocation view */
    invocationCreateTime?: string;
    historyId: string;
    showDetails?: boolean;
    hideHr?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    invocationCreateTime: undefined,
});

const { workflow, owned } = useWorkflowInstance(props.workflowId);

const description = computed(() => {
    return workflow.value?.annotation?.trim() || null;
});

const timeElapsed = computed(() => {
    return props.invocationCreateTime || workflow.value?.update_time;
});

const workflowTags = computed(() => {
    return workflow.value?.tags || [];
});
</script>

<template>
    <div v-if="workflow" class="pb-2 pl-2">
        <div
            class="d-flex justify-content-between align-items-center"
            :class="{ 'has-annotation-middle': props.invocationCreateTime }">
            <div class="annotation-left">
                <i v-if="timeElapsed" data-description="workflow annotation time info">
                    <FontAwesomeIcon :icon="faClock" class="mr-1" />
                    <span v-localize>
                        {{ props.invocationCreateTime ? "invoked" : "edited" }}
                    </span>
                    <UtcDate :date="timeElapsed" mode="elapsed" data-description="workflow annotation date" />
                </i>
                <TargetHistoryLink v-if="props.invocationCreateTime" :target-history-id="props.historyId" />
            </div>
            <div v-if="props.invocationCreateTime" class="annotation-middle">
                <slot name="middle-content" />
            </div>
            <div class="annotation-right">
                <div class="annotation-right-content">
                    <WorkflowIndicators :workflow="workflow" published-view no-edit-time />
                    <WorkflowInvocationsCount v-if="owned" class="mr-1" :workflow="workflow" />
                </div>
            </div>
        </div>
        <div v-if="props.showDetails">
            <TextSummary v-if="description" class="my-1" :description="description" component="span" />
            <StatelessTags v-if="workflowTags.length" :value="workflowTags" :disabled="true" />
            <hr v-if="!props.hideHr" class="mb-0 mt-2" />
        </div>
    </div>
</template>

<style scoped lang="scss">
.annotation-left {
    flex: 1 1 0;
    min-width: 0;
    overflow: hidden;

    // Ensure neither the history name nor "(current)" escape the column.
    :deep(.history-link-wrapper) {
        min-width: 0;
        overflow: hidden;
    }

    // SwitchToHistoryLink root div must be able to shrink to 0 so the
    // "(current)" label stays visible as long as there is any room.
    :deep(.history-link-wrapper > div) {
        min-width: 0;
        overflow: hidden;
    }

    :deep(.history-link) {
        min-width: 0;
    }

    :deep(.history-link-click) {
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
        display: block;
    }
}

.annotation-middle {
    flex: 1 1 0;
    min-width: 0;
}

.annotation-right {
    flex: 1 1 0;
    min-width: 0;
    overflow: hidden;
    justify-content: flex-end;

    .annotation-right-content {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 0.25rem;
        min-width: 0;
        overflow: hidden;
    }

    // Ensure creator badges stay within the column instead of overflowing
    :deep(.workflow-indicators) {
        flex-wrap: wrap;
        justify-content: flex-end;
    }
}

// When the middle column is rendered (invocation view), give all
// fixed widths so the progress bars in middle are not constrained
.has-annotation-middle {
    .annotation-left {
        max-width: 35%;
    }

    .annotation-middle {
        max-width: 30%;
    }

    .annotation-right {
        max-width: 35%;
    }
}
</style>
