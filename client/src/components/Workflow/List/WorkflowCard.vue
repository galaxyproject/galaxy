<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { type WorkflowSummary } from "@/api/workflows";
import { useWorkflowCardActions } from "@/components/Workflow/List/useWorkflowCardActions";
import { useWorkflowCardBadges } from "@/components/Workflow/List/useWorkflowCardBadges";
import { useWorkflowCardIndicators } from "@/components/Workflow/List/useWorkflowCardIndicators";
import { updateWorkflow } from "@/components/Workflow/workflows.services";
import { useUserStore } from "@/stores/userStore";

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

async function onTagsUpdate(tags: string[]) {
    workflow.value.tags = tags;
    await updateWorkflow(workflow.value.id, { tags });
    emit("refreshList", true, true);
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
        () => emit("insert"),
        () => emit("insertSteps")
    );

const { workflowCardIndicators } = useWorkflowCardIndicators(
    computed(() => props.workflow),
    props.publishedView,
    props.filterable,
    (key, value) => emit("updateFilter", key, value)
);

const { workflowCardBadges } = useWorkflowCardBadges(
    computed(() => props.workflow),
    props.publishedView,
    props.filterable,
    props.hideRuns,
    (key, value) => emit("updateFilter", key, value)
);

const workflowCardTitle = computed(() => {
    return {
        label: workflow.value.name,
        title: "Preview Workflow",
        handler: () => emit("preview", props.workflow.id),
    };
});
</script>

<template>
    <GCard
        :id="workflow.id"
        class="workflow-card"
        can-rename-title
        :title="workflowCardTitle"
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
        @bookmark="() => toggleBookmark(!workflow?.show_in_tool_panel)"
        @rename="emit('rename', props.workflow.id, props.workflow.name)"
        @select="emit('select', workflow)"
        @tagsUpdate="onTagsUpdate"
        @tagClick="onTagClick">
        <template v-if="props.current" v-slot:primary-actions>
            <i class="mr-2"> current workflow </i>
        </template>
    </GCard>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "_breakpoints.scss";

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
