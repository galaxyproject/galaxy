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
import { BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { undeleteWorkflow } from "@/components/Workflow/workflows.services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import { useWorkflowActions } from "./useWorkflowActions";

import AsyncButton from "@/components/Common/AsyncButton.vue";
import WorkflowRunButton from "@/components/Workflow/WorkflowRunButton.vue";

interface Props {
    workflow: any;
    published?: boolean;
    editor?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    published: false,
    editor: false,
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
        <BButtonGroup>
            <template v-if="!props.editor && !workflow.deleted">
                <BButton
                    v-if="workflow.published"
                    id="workflow-copy-public-button"
                    v-b-tooltip.hover.noninteractive
                    size="sm"
                    title="Copy link to workflow"
                    variant="outline-primary"
                    @click="copyPublicLink">
                    <FontAwesomeIcon :icon="faLink" fixed-width />
                    <span class="compact-view">Link to Workflow</span>
                </BButton>

                <BButton
                    v-if="!isAnonymous && !shared"
                    id="workflow-copy-button"
                    v-b-tooltip.hover.noninteractive
                    size="sm"
                    title="Copy"
                    variant="outline-primary"
                    @click="copyWorkflow">
                    <FontAwesomeIcon :icon="faCopy" fixed-width />
                    <span class="compact-view">Copy</span>
                </BButton>

                <BButton
                    id="workflow-download-button"
                    v-b-tooltip.hover.noninteractive
                    size="sm"
                    title="Download workflow in .ga format"
                    variant="outline-primary"
                    :href="downloadUrl">
                    <FontAwesomeIcon :icon="faDownload" fixed-width />
                    <span class="compact-view">Download</span>
                </BButton>

                <BButton
                    v-if="!isAnonymous && !shared"
                    id="workflow-share-button"
                    v-b-tooltip.hover.noninteractive
                    size="sm"
                    title="Share"
                    variant="outline-primary"
                    :to="`/workflows/sharing?id=${workflow.id}`">
                    <FontAwesomeIcon :icon="faShareAlt" fixed-width />
                    <span class="compact-view">Share</span>
                </BButton>
            </template>

            <BButton
                v-if="workflow.deleted"
                id="restore-button"
                v-b-tooltip.hover.noninteractive
                size="sm"
                title="Restore"
                variant="outline-primary"
                @click="onRestore">
                <FontAwesomeIcon :icon="faTrashRestore" fixed-width />
                <span class="compact-view">Restore</span>
            </BButton>
        </BButtonGroup>

        <div>
            <BButton
                v-if="!isAnonymous && !shared"
                v-b-tooltip.hover.noninteractive
                :disabled="workflow.deleted"
                size="sm"
                class="workflow-edit-button"
                :title="editButtonTitle"
                variant="outline-primary"
                :to="`/workflows/edit?id=${workflow.id}`">
                <FontAwesomeIcon :icon="faEdit" fixed-width />
                Edit
            </BButton>

            <AsyncButton
                v-else
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

            <BButtonGroup v-if="props.editor && !workflow.deleted">
                <BButton
                    v-b-tooltip.hover.noninteractive
                    size="sm"
                    title="Copy steps into workflow"
                    variant="outline-primary"
                    @click="emit('insertSteps')">
                    <FontAwesomeIcon :icon="faCopy" fixed-width />
                </BButton>

                <BButton
                    v-b-tooltip.hover.noninteractive
                    size="sm"
                    title="Insert as sub-workflow"
                    variant="primary"
                    @click="emit('insert')">
                    <FontAwesomeIcon :icon="faPlusSquare" fixed-width />
                    <span> Insert </span>
                </BButton>
            </BButtonGroup>
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
    justify-content: end;

    @container (max-width: #{$breakpoint-md}) {
        .compact-view {
            display: none;
        }
    }
}
</style>
