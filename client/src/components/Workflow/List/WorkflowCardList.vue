<script setup lang="ts">
import { reactive, ref } from "vue";

import type { WorkflowSummary } from "@/api/workflows";

import type { SelectedWorkflow } from "./types";

import WorkflowCard from "./WorkflowCard.vue";
import WorkflowRename from "./WorkflowRename.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import WorkflowPublished from "@/components/Workflow/Published/WorkflowPublished.vue";
import WorkflowPublishedButtons from "@/components/Workflow/Published/WorkflowPublishedButtons.vue";

interface Props {
    workflows: WorkflowSummary[];
    gridView?: boolean;
    hideRuns?: boolean;
    filterable?: boolean;
    publishedView?: boolean;
    editorView?: boolean;
    currentWorkflowId?: string;
    selectedWorkflowIds?: SelectedWorkflow[];
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
    hideRuns: false,
    filterable: true,
    publishedView: false,
    editorView: false,
    currentWorkflowId: "",
    selectedWorkflowIds: () => [],
});

const emit = defineEmits<{
    (e: "select", workflow: WorkflowSummary): void;
    (e: "tagClick", tag: string): void;
    (e: "refreshList", overlayLoading?: boolean, silent?: boolean): void;
    (e: "updateFilter", key: string, value: any): void;
    (e: "insertWorkflow", id: string, name: string): void;
    (e: "insertWorkflowSteps", id: string, stepCount: number): void;
}>();

const modalOptions = reactive({
    rename: {
        id: "",
        name: "",
    },
    preview: {
        id: "",
    },
});

const showRename = ref(false);
const showPreview = ref(false);

function onRenameClose() {
    showRename.value = false;
    emit("refreshList", true, true);
}

function onRename(id: string, name: string) {
    modalOptions.rename.id = id;
    modalOptions.rename.name = name;
    showRename.value = true;
}

function onPreview(id: string) {
    modalOptions.preview.id = id;
    showPreview.value = true;
}

// TODO: clean-up types, as soon as better Workflow type is available
function onInsert(workflow: WorkflowSummary) {
    emit("insertWorkflow", workflow.latest_workflow_id, workflow.name);
}

function onInsertSteps(workflow: WorkflowSummary) {
    emit("insertWorkflowSteps", workflow.id, workflow.number_of_steps as any);
}

const workflowPublished = ref<InstanceType<typeof WorkflowPublished>>();
</script>

<template>
    <div class="workflow-card-list d-flex flex-wrap overflow-auto">
        <WorkflowCard
            v-for="workflow in workflows"
            :key="workflow.id"
            :workflow="workflow"
            :selectable="!publishedView && !editorView"
            :selected="props.selectedWorkflowIds.some((w) => w.id === workflow.id)"
            :grid-view="props.gridView"
            :hide-runs="props.hideRuns"
            :filterable="props.filterable"
            :published-view="props.publishedView"
            :editor-view="props.editorView"
            :current="workflow.id === props.currentWorkflowId"
            @select="(...args) => emit('select', ...args)"
            @tagClick="(...args) => emit('tagClick', ...args)"
            @refreshList="(...args) => emit('refreshList', ...args)"
            @updateFilter="(...args) => emit('updateFilter', ...args)"
            @rename="onRename"
            @preview="onPreview"
            @insert="onInsert(workflow)"
            @insertSteps="onInsertSteps(workflow)" />

        <WorkflowRename
            :id="modalOptions.rename.id"
            :show="showRename"
            :name="modalOptions.rename.name"
            @close="onRenameClose" />

        <GModal
            :show.sync="showPreview"
            size="large"
            title="Workflow Preview"
            hide-header
            fixed-height
            class="workflow-card-preview-modal"
            centered>
            <template v-slot:header>
                <WorkflowPublishedButtons
                    v-if="workflowPublished?.workflowInfo"
                    :id="modalOptions.preview.id"
                    :workflow-info="workflowPublished?.workflowInfo" />
            </template>

            <WorkflowPublished
                v-if="showPreview"
                :id="modalOptions.preview.id"
                ref="workflowPublished"
                :show-heading="false"
                :show-buttons="false"
                quick-view />
        </GModal>
    </div>
</template>

<style lang="scss">
.workflow-card-preview-modal {
    max-width: min(1400px, calc(100% - 200px));

    .modal-content {
        height: min(800px, calc(100vh - 80px));
    }
}
</style>

<style scoped lang="scss">
@import "_breakpoints.scss";

.workflow-card-list {
    container: cards-list / inline-size;
}
</style>
