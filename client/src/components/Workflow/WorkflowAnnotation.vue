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
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <i v-if="timeElapsed" data-description="workflow annotation time info">
                    <FontAwesomeIcon :icon="faClock" class="mr-1" />
                    <span v-localize>
                        {{ props.invocationCreateTime ? "invoked" : "edited" }}
                    </span>
                    <UtcDate :date="timeElapsed" mode="elapsed" data-description="workflow annotation date" />
                </i>
                <TargetHistoryLink v-if="props.invocationCreateTime" :target-history-id="props.historyId" />
            </div>
            <slot name="middle-content" />
            <div class="d-flex align-items-center">
                <div class="d-flex flex-column align-items-end mr-2 flex-gapy-1">
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
.history-link-wrapper {
    max-width: 300px;

    &:deep(.history-link) {
        .history-link-click {
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            display: block;
        }
    }
}
</style>
