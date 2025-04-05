<script setup lang="ts">
import {
    faCopy,
    faDownload,
    faEdit,
    faLink,
    faPlusSquare,
    faShareAlt,
    faTrashRestore,
    faUpload,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { type AnyWorkflow, undeleteWorkflow } from "@/api/workflows";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import { useWorkflowActions } from "./useWorkflowActions";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import AsyncButton from "@/components/Common/AsyncButton.vue";
import WorkflowRunButton from "@/components/Workflow/WorkflowRunButton.vue";

interface Props {
    workflow: AnyWorkflow;
    published?: boolean;
    editor?: boolean;
    current?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    published: false,
    editor: false,
    current: false,
});

const emit = defineEmits<{
    (e: "refreshList", overlayLoading?: boolean): void;
    (e: "insert"): void;
    (e: "insertSteps"): void;
}>();

const userStore = useUserStore();
const { confirm } = useConfirmDialog();
const { isAnonymous } = storeToRefs(useUserStore());

const shared = computed(() => {
    return !userStore.matchesCurrentUsername(props.workflow.owner);
});

async function onRestore() {
    const confirmed = await confirm("Are you sure you want to restore this workflow?", "Restore workflow");

    if (confirmed) {
        await undeleteWorkflow(props.workflow.id);
        emit("refreshList", true);
        Toast.info("Workflow restored");
    }
}

const editButtonTitle = computed(() => {
    if (isAnonymous.value) {
        return "Log in to edit Workflow";
    } else {
        if (props.workflow.deleted) {
            return "You cannot edit a deleted workflow. Restore it first.";
        } else {
            return "Edit Workflow";
        }
    }
});
const importedButtonTitle = computed(() => {
    if (isAnonymous.value) {
        return "Log in to import workflow";
    } else {
        return "Import this workflow to edit";
    }
});
const runButtonTitle = computed(() => {
    if (isAnonymous.value) {
        return "Log in to run workflow";
    } else {
        if (props.workflow.deleted) {
            return "You cannot run a deleted workflow. Restore it first.";
        } else {
            return "Run workflow";
        }
    }
});

const { copyPublicLink, copyWorkflow, downloadUrl, importWorkflow } = useWorkflowActions(
    computed(() => props.workflow),
    () => emit("refreshList", true)
);
</script>

<template>
    <div class="workflow-card-actions flex-gapx-1">
        <GButtonGroup>
            <template v-if="!props.editor && !workflow.deleted">
                <GButton
                    v-if="workflow.published"
                    id="workflow-copy-public-button"
                    tooltip
                    outline
                    size="small"
                    color="blue"
                    title="Copy link to workflow"
                    @click="copyPublicLink">
                    <FontAwesomeIcon :icon="faLink" fixed-width />
                    <span class="compact-view">Link to Workflow</span>
                </GButton>

                <GButton
                    v-if="!isAnonymous && !shared"
                    id="workflow-copy-button"
                    tooltip
                    outline
                    size="small"
                    color="blue"
                    title="Copy"
                    @click="copyWorkflow">
                    <FontAwesomeIcon :icon="faCopy" fixed-width />
                    <span class="compact-view">Copy</span>
                </GButton>

                <GButton
                    id="workflow-download-button"
                    tooltip
                    outline
                    size="small"
                    color="blue"
                    title="Download workflow in .ga format"
                    :href="downloadUrl">
                    <FontAwesomeIcon :icon="faDownload" fixed-width />
                    <span class="compact-view">Download</span>
                </GButton>

                <GButton
                    v-if="!isAnonymous && !shared"
                    id="workflow-share-button"
                    tooltip
                    outline
                    size="small"
                    color="blue"
                    title="Share"
                    :to="`/workflows/sharing?id=${workflow.id}`">
                    <FontAwesomeIcon :icon="faShareAlt" fixed-width />
                    <span class="compact-view">Share</span>
                </GButton>
            </template>

            <GButton
                v-if="workflow.deleted"
                id="restore-button"
                tooltip
                outline
                size="small"
                color="blue"
                title="Restore"
                @click="onRestore">
                <FontAwesomeIcon :icon="faTrashRestore" fixed-width />
                <span class="compact-view">Restore</span>
            </GButton>
        </GButtonGroup>

        <div class="d-flex flex-gapx-1 align-items-center">
            <i v-if="props.current" class="mr-2"> current workflow </i>

            <GButton
                v-if="!isAnonymous && !shared && !props.current"
                :disabled="workflow.deleted"
                tooltip
                outline
                size="small"
                color="blue"
                class="workflow-edit-button"
                :title="editButtonTitle"
                :to="`/workflows/edit?id=${workflow.id}`">
                <FontAwesomeIcon :icon="faEdit" fixed-width />
                Edit
            </GButton>

            <AsyncButton
                v-else-if="!props.current"
                v-b-tooltip.hover.noninteractive
                size="sm"
                :disabled="isAnonymous"
                :title="importedButtonTitle"
                :icon="faUpload"
                variant="outline-primary"
                :action="importWorkflow">
                Import
            </AsyncButton>

            <WorkflowRunButton
                v-if="!props.editor"
                :id="workflow.id"
                :disabled="isAnonymous || workflow.deleted"
                :title="runButtonTitle" />

            <GButtonGroup v-if="props.editor && !workflow.deleted">
                <GButton
                    tooltip
                    outline
                    size="small"
                    color="blue"
                    title="Copy steps into workflow"
                    @click="emit('insertSteps')">
                    <FontAwesomeIcon :icon="faCopy" fixed-width />
                </GButton>

                <GButton
                    v-if="!props.current"
                    tooltip
                    outline
                    size="small"
                    color="blue"
                    title="Insert as sub-workflow"
                    @click="emit('insert')">
                    <FontAwesomeIcon :icon="faPlusSquare" fixed-width />
                    <span> Insert </span>
                </GButton>
            </GButtonGroup>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "_breakpoints.scss";

.workflow-card-actions {
    display: flex;
    gap: 0.25rem;
    margin-top: 0.25rem;
    align-items: center;
    justify-content: flex-end;

    @container (max-width: #{$breakpoint-md}) {
        .compact-view {
            display: none;
        }
    }
}
</style>
