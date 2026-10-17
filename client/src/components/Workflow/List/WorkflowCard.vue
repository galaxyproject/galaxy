<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { WorkflowSummary } from "@/api/workflows";
import { useWorkflowCardActions } from "@/components/Workflow/List/useWorkflowCardActions";
import { useWorkflowCardBadges } from "@/components/Workflow/List/useWorkflowCardBadges";
import { useWorkflowCardIndicators } from "@/components/Workflow/List/useWorkflowCardIndicators";
import { updateWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import GCard from "@/components/Common/GCard.vue";

interface Props {
    workflow: WorkflowSummary;
    gridView?: boolean;
    hideRuns?: boolean;
    filterable?: boolean;
    publishedView?: boolean;
    editorView?: boolean;
    current?: boolean;
    selected?: boolean;
    selectable?: boolean;
    clickable?: boolean;
    highlighted?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
    publishedView: false,
    hideRuns: false,
    filterable: true,
    editorView: false,
    current: false,
    selected: false,
    selectable: false,
    clickable: false,
    highlighted: false,
});

const emit = defineEmits<{
    (e: "select", workflow: any): void;
    (e: "tagClick", tag: string): void;
    (e: "refreshList", overlayLoading?: boolean, silent?: boolean): void;
    (e: "updateFilter", key: string, value: any): void;
    (e: "rename", id: string, name: string): void;
    (e: "preview", id: string): void;
    (e: "insert"): void;
    (e: "insertSteps"): void;
    (e: "on-key-down", workflow: WorkflowSummary, event: KeyboardEvent): void;
    (e: "on-workflow-card-click", workflow: WorkflowSummary, event: Event): void;
}>();

const userStore = useUserStore();

const { isAnonymous } = storeToRefs(userStore);

const workflow = computed(() => props.workflow);

const shared = computed(() => {
    return !userStore.matchesCurrentUsername(workflow.value.owner);
});

const description = computed(() => {
    if (workflow.value.annotations && workflow.value.annotations.length > 0) {
        return workflow.value.annotations[0]?.trim();
    } else {
        return null;
    }
});

/** Tag saves run one after another, so an older tag list never lands after a newer one. */
let tagsSaved: Promise<void> = Promise.resolve();
let pendingTagSaves = 0;
let lastSavedTags: string[] | undefined;
let lastTagSaveFailed = false;

function onTagsUpdate(tags: string[]) {
    // updated in place: a list reload re-sorts the list and moves the card away from the open tag editor
    workflow.value.tags = tags;
    const workflowId = workflow.value.id;
    pendingTagSaves++;
    tagsSaved = tagsSaved.then(async () => {
        try {
            await updateWorkflow(workflowId, { tags });
            lastSavedTags = tags;
            lastTagSaveFailed = false;
        } catch (error) {
            Toast.error(`Failed to save tags: ${errorMessageAsString(error)}`);
            lastTagSaveFailed = true;
        } finally {
            pendingTagSaves--;
            if (pendingTagSaves === 0) {
                onTagSavesDone();
            }
        }
    });
}

function onTagSavesDone() {
    if (lastTagSaveFailed) {
        emit("refreshList", true, true);
    } else if (lastSavedTags && !sameTags(workflow.value.tags, lastSavedTags)) {
        // a list load that ran during the saves can hold the tags from before them
        workflow.value.tags = lastSavedTags;
    }
}

function sameTags(a: string[], b: string[]) {
    return a.length === b.length && a.every((tag, index) => tag === b[index]);
}

async function onTagClick(tag: string) {
    emit("tagClick", tag);
}

const { workflowCardExtraActions, workflowCardSecondaryActions, workflowCardPrimaryActions, toggleBookmark } =
    useWorkflowCardActions(
        computed(() => props.workflow),
        props.current,
        props.editorView,
        () => emit("refreshList", true),
        () => emit("insertSteps"),
        () => emit("insert"),
    );

const { workflowCardIndicators } = useWorkflowCardIndicators(
    computed(() => props.workflow),
    props.publishedView,
    props.filterable,
    (key, value) => emit("updateFilter", key, value),
);

const { workflowCardBadges, workflowCardTitleBadges } = useWorkflowCardBadges(
    computed(() => props.workflow),
    props.publishedView,
    props.filterable,
    props.hideRuns,
    (key, value) => emit("updateFilter", key, value),
);

const workflowCardTitle = computed(() => {
    return {
        label: workflow.value.name,
        title: localize("Click to preview workflow"),
        handler: () => emit("preview", props.workflow.id),
    };
});

function onClick(event: Event) {
    if (props.clickable) {
        emit("on-workflow-card-click", workflow.value, event);
    }
}

function onKeyDown(event: KeyboardEvent) {
    if (props.clickable) {
        emit("on-key-down", workflow.value, event);
    }
}
</script>

<template>
    <GCard
        :id="workflow.id"
        class="workflow-card"
        :can-rename-title="!props.workflow.deleted"
        :title="workflowCardTitle"
        :title-badges="workflowCardTitleBadges"
        :title-n-lines="2"
        :description="description || ''"
        :grid-view="props.gridView"
        :badges="workflowCardBadges"
        :indicators="workflowCardIndicators"
        :extra-actions="workflowCardExtraActions"
        :primary-actions="workflowCardPrimaryActions"
        :secondary-actions="workflowCardSecondaryActions"
        :published="workflow.published"
        :selectable="props.selectable && !shared"
        :selected="props.selected"
        :show-bookmark="!props.workflow.deleted"
        :tags="workflow.tags"
        :tags-editable="!props.current && !isAnonymous && !workflow.deleted && !shared"
        :max-visible-tags="props.gridView ? 2 : 8"
        :update-time="workflow.update_time"
        :bookmarked="!!workflow.show_in_tool_panel"
        :clickable="props.clickable"
        :highlighted="props.highlighted"
        @bookmark="() => toggleBookmark(!workflow?.show_in_tool_panel)"
        @rename="emit('rename', props.workflow.id, props.workflow.name)"
        @select="emit('select', workflow)"
        @tagsUpdate="onTagsUpdate"
        @tagClick="onTagClick"
        @click="onClick"
        @keydown="onKeyDown">
        <template v-if="props.current" v-slot:primary-actions>
            <i class="mr-2"> current workflow </i>
        </template>
    </GCard>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";
@import "@/style/scss/_breakpoints.scss";

.workflow-card {
    .workflow-rename {
        visibility: hidden;
    }

    &:hover,
    &:focus-within {
        .workflow-rename {
            visibility: visible;
        }
    }
}
</style>
