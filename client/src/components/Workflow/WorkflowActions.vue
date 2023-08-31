<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import {
    faCopy,
    faDownload,
    faEye,
    faFileExport,
    faShareAlt,
    faStar,
    faTrash,
    faTrashRestore,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import {
    copyWorkflow,
    deleteWorkflow,
    undeleteWorkflow,
    updateWorkflow,
} from "@/components/Workflow/workflows.services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import AsyncButton from "@/components/Common/AsyncButton.vue";

library.add(faCopy, faDownload, faEye, faFileExport, faShareAlt, farStar, faStar, faTrash, faTrashRestore);

interface Props {
    workflow: any;
    showControls: boolean;
    buttonSize?: "sm" | "md" | "lg";
}

const props = withDefaults(defineProps<Props>(), {
    buttonSize: "sm",
});

const emit = defineEmits<{
    (e: "refreshList", a?: boolean): void;
    (e: "toggleShowPreview", a?: boolean): void;
}>();

const router = useRouter();
const userStore = useUserStore();
const { confirm } = useConfirmDialog();
const { isAnonymous } = storeToRefs(useUserStore());

const downloadUrl = computed(() => {
    return `/api/workflows/${props.workflow.id}/download?format=json-download`;
});
const shared = computed(() => {
    if (userStore.currentUser) {
        return userStore.currentUser.username !== props.workflow.owner;
    } else {
        return false;
    }
});

function onExport() {
    router.push(`/workflows/export?id=${props.workflow.id}`);
}

function onShare() {
    router.push(`/workflows/sharing?id=${props.workflow.id}`);
}

async function onCopy() {
    const confirmed = await confirm("Are you sure you want to make a copy of this workflow?", "Copy workflow");

    if (confirmed) {
        await copyWorkflow(props.workflow.id, props.workflow.owner);
        emit("refreshList", true);
        Toast.success("Workflow copied");
    }
}

async function onToggleBookmark(checked: boolean) {
    await updateWorkflow(props.workflow.id, {
        show_in_tool_panel: checked,
    });
    emit("refreshList", true);
    Toast.info(`Workflow ${checked ? "added to" : "removed from"} bookmarks`);
}

async function onDelete() {
    const confirmed = await confirm("Are you sure you want to delete this workflow?", "Delete workflow");

    if (confirmed) {
        await deleteWorkflow(props.workflow.id);
        emit("refreshList", true);
        Toast.info("Workflow deleted");
    }
}

async function onRestore() {
    const confirmed = await confirm("Are you sure you want to restore this workflow?", "Restore workflow");

    if (confirmed) {
        await undeleteWorkflow(props.workflow.id);
        emit("refreshList", true);
        Toast.info("Workflow restored");
    }
}
</script>

<template>
    <div class="workflow-actions d-flex align-items-baseline flex-wrap justify-content-end">
        <AsyncButton
            v-if="!shared && !workflow.deleted"
            id="delete-button"
            v-b-tooltip.top
            :class="{ 'mouse-out': !props.showControls }"
            :size="buttonSize"
            title="Delete workflow"
            :icon="faTrash"
            :action="() => onDelete()" />

        <AsyncButton
            v-if="!isAnonymous && !workflow.deleted"
            id="copy-button"
            v-b-tooltip.top
            :class="{ 'mouse-out': !props.showControls }"
            :size="buttonSize"
            title="Copy workflow"
            :icon="faCopy"
            :action="() => onCopy()" />

        <BButton
            v-if="!shared && !workflow.deleted"
            id="export-button"
            v-b-tooltip.top
            :class="{ 'mouse-out': !props.showControls }"
            variant="link"
            :size="buttonSize"
            title="Export workflow"
            @click="onExport">
            <FontAwesomeIcon :icon="faFileExport" />
        </BButton>

        <BButton
            v-if="!workflow.deleted"
            id="download-button"
            v-b-tooltip.top
            :class="{ 'mouse-out': !props.showControls }"
            variant="link"
            :size="buttonSize"
            title="Download workflow"
            :href="downloadUrl">
            <FontAwesomeIcon :icon="faDownload" />
        </BButton>

        <BButton
            v-if="!shared && !workflow.deleted"
            id="share-button"
            v-b-tooltip.top
            :class="{ 'mouse-out': !props.showControls }"
            variant="link"
            :size="buttonSize"
            title="Share workflow"
            @click="onShare">
            <FontAwesomeIcon :icon="faShareAlt" />
        </BButton>

        <BButton
            v-if="workflow.deleted"
            id="restore-button"
            v-b-tooltip.top
            :class="{ 'mouse-out': !props.showControls }"
            variant="link"
            :size="buttonSize"
            title="Restore workflow"
            @click="onRestore">
            <FontAwesomeIcon :icon="faTrashRestore" />
        </BButton>

        <BButton
            id="view-button"
            v-b-tooltip.top
            :class="{ 'mouse-out': !props.showControls }"
            variant="link"
            :size="buttonSize"
            title="View workflow"
            @click="emit('toggleShowPreview', true)">
            <FontAwesomeIcon :icon="faEye" />
        </BButton>

        <AsyncButton
            v-if="workflow.show_in_tool_panel"
            id="remove-bookmark-button"
            title="Remove bookmark"
            :class="{ 'mouse-out': !props.showControls }"
            :icon="faStar"
            :size="buttonSize"
            :action="() => onToggleBookmark(false)" />

        <AsyncButton
            v-else
            id="add-bookmark-button"
            :class="{ 'mouse-out': !props.showControls }"
            title="Add a bookmark. This workflow will appear in the left tool panel."
            :icon="farStar"
            :size="buttonSize"
            :action="() => onToggleBookmark(true)" />
    </div>
</template>

<style scoped lang="scss">
.workflow-actions {
    .mouse-out {
        opacity: 0.5;
    }
}
</style>
