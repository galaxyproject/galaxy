<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faExclamation, faHdd } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { isRegisteredUser } from "@/api";
import { useMarkdown } from "@/composables/markdown";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import { fetchReadmeForIwcWorkflow } from "./workflows.services";

import Heading from "../Common/Heading.vue";
import TextSummary from "../Common/TextSummary.vue";
import SwitchToHistoryLink from "../History/SwitchToHistoryLink.vue";
import LoadingSpan from "../LoadingSpan.vue";
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

const readme = ref<string | null>(null);
const readMeLoading = ref<boolean | null>(null);
const readMeShown = ref(false);

watch(
    () => workflow.value,
    async (wf) => {
        if (wf && props.showDetails) {
            await setReadmeIfExists();
        }
    },
    { immediate: true }
);

const { renderMarkdown } = useMarkdown({
    openLinksInNewPage: true,
    removeNewlinesAfterList: true,
    increaseHeadingLevelBy: 1,
});

async function setReadmeIfExists() {
    const sourceMetadata = workflow.value?.source_metadata;
    if (sourceMetadata && "trs_tool_id" in sourceMetadata && typeof sourceMetadata.trs_tool_id === "string") {
        try {
            readMeLoading.value = true;
            const fetchedReadme = await fetchReadmeForIwcWorkflow(sourceMetadata.trs_tool_id);
            if (fetchedReadme) {
                readme.value = renderMarkdown(fetchedReadme);
            }
        } catch (error) {
            // there is no readme
        } finally {
            readMeLoading.value = false;
        }
    }
}
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
                <span v-if="invocationUpdateTime" class="d-flex flex-gapx-1 align-items-center">
                    <FontAwesomeIcon :icon="faHdd" />History:
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
            <TextSummary v-if="description" class="my-1" :description="description" one-line-summary component="span" />
            <StatelessTags v-if="workflowTags.length" :value="workflowTags" :disabled="true" />
            <BAlert v-if="readMeLoading" variant="info" show>
                <LoadingSpan message="Loading workflow README" />
            </BAlert>
            <div v-else-if="readme" class="mt-2">
                <Heading
                    h2
                    separator
                    bold
                    size="sm"
                    :collapse="readMeShown ? 'open' : 'closed'"
                    @click="readMeShown = !readMeShown">
                    <span v-localize>Help</span>
                </Heading>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <p v-if="readMeShown" v-html="readme" />
            </div>
            <hr class="mb-0 mt-2" />
        </div>
    </div>
</template>
