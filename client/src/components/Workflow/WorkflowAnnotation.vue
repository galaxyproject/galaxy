<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faExclamation, faHdd } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { isRegisteredUser } from "@/api";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import TextSummary from "../Common/TextSummary.vue";
import SwitchToHistoryLink from "../History/SwitchToHistoryLink.vue";
import StatelessTags from "../TagsMultiselect/StatelessTags.vue";
import UtcDate from "../UtcDate.vue";
import WorkflowInvocationsCount from "../Workflow/WorkflowInvocationsCount.vue";
import WorkflowIndicators from "@/components/Workflow/List/WorkflowIndicators.vue";

interface Props {
    workflowId: string;
    invocationUpdateTime?: string;
    historyId: string;
    showDetails?: boolean;
    newHistoryTarget?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    invocationUpdateTime: undefined,
});

const { workflow } = useWorkflowInstance(props.workflowId);

const { currentUser } = storeToRefs(useUserStore());
const owned = computed(() => {
    if (isRegisteredUser(currentUser.value) && workflow.value) {
        return currentUser.value.username === workflow.value.owner;
    } else {
        return false;
    }
});

const description = computed(() => {
    if (workflow.value?.annotation) {
        return workflow.value.annotation?.trim();
    } else {
        return null;
    }
});

const timeElapsed = computed(() => {
    return props.invocationUpdateTime || workflow.value?.update_time;
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
                        {{ props.invocationUpdateTime ? "invoked" : "edited" }}
                    </span>
                    <UtcDate :date="timeElapsed" mode="elapsed" data-description="workflow annotation date" />
                </i>
                <span class="d-flex flex-gapx-1 align-items-center">
                    <FontAwesomeIcon :icon="faHdd" />Input History:
                    <SwitchToHistoryLink :history-id="props.historyId" />
                    <BBadge
                        v-if="props.newHistoryTarget && useHistoryStore().currentHistoryId !== props.historyId"
                        v-b-tooltip.hover.noninteractive
                        data-description="new history badge"
                        role="button"
                        variant="info"
                        title="Results generated in a new history. Click on history name to switch to that history.">
                        <FontAwesomeIcon :icon="faExclamation" />
                    </BBadge>
                </span>
            </div>
            <slot name="middle-content" />
            <div class="d-flex align-items-center">
                <div class="d-flex flex-column align-items-end mr-2">
                    <WorkflowIndicators :workflow="workflow" published-view no-edit-time />
                    <WorkflowInvocationsCount v-if="owned" class="mr-1" :workflow="workflow" />
                </div>
            </div>
        </div>
        <div v-if="props.showDetails">
            <TextSummary v-if="description" class="my-1" :description="description" />
            <StatelessTags v-if="workflowTags.length" :value="workflowTags" :disabled="true" />
        </div>
    </div>
</template>
