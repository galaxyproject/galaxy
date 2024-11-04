<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faChevronDown, faChevronUp, faHdd } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { isRegisteredUser } from "@/api";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useUserStore } from "@/stores/userStore";

import TextSummary from "../Common/TextSummary.vue";
import SwitchToHistoryLink from "../History/SwitchToHistoryLink.vue";
import StatelessTags from "../TagsMultiselect/StatelessTags.vue";
import UtcDate from "../UtcDate.vue";
import WorkflowInvocationsCount from "../Workflow/WorkflowInvocationsCount.vue";
import WorkflowIndicators from "@/components/Workflow/List/WorkflowIndicators.vue";

library.add(faChevronDown, faChevronUp);

interface Props {
    workflowId: string;
    invocationUpdateTime?: string;
    historyId: string;
    showDetails?: boolean;
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

const workflowTags = computed(() => {
    return workflow.value?.tags || [];
});
</script>

<template>
    <div v-if="workflow" class="pb-2 pl-2">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <i v-if="props.invocationUpdateTime">
                    <FontAwesomeIcon :icon="faClock" class="mr-1" />invoked
                    <UtcDate :date="props.invocationUpdateTime" mode="elapsed" />
                </i>
                <i v-else-if="workflow.update_time">
                    <FontAwesomeIcon :icon="faClock" class="mr-1" />edited
                    <UtcDate :date="workflow.update_time" mode="elapsed" />
                </i>
                <span v-if="invocationUpdateTime" class="d-flex flex-gapx-1 align-items-center">
                    <FontAwesomeIcon :icon="faHdd" />History:
                    <SwitchToHistoryLink :history-id="props.historyId" />
                </span>
            </div>
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
