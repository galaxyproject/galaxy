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
    menu?: boolean;
    published?: boolean;
    showControls: boolean;
    buttonSize?: "sm" | "md" | "lg";
}

type BaseAction = {
    if?: boolean;
    id: string;
    title: string;
    tooltip: string;
    icon: any;
    href?: string;
    size: "sm" | "md" | "lg";
    component: "async" | "button";
    variant: "primary" | "secondary" | "success" | "danger" | "warning" | "info" | "light" | "dark" | "link";
    onClick?: () => Promise<void> | void;
};

interface AAction extends BaseAction {
    component: "async";
    action: () => Promise<void>;
}

interface BAction extends BaseAction {
    component: "button";
    href?: string;
    onClick?: () => Promise<void> | void;
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

const actions: (AAction | BAction)[] = [
    {
        if: !shared.value && !props.workflow.deleted,
        id: "delete-button",
        component: "button",
        title: "Delete workflow",
        tooltip: "Delete workflow",
        icon: faTrash,
        size: props.buttonSize,
        variant: "link",
        onClick: () => onDelete(),
    },
    {
        if: !isAnonymous.value && !props.workflow.deleted,
        id: "copy-button",
        component: "button",
        title: "Copy workflow",
        tooltip: "Copy workflow",
        icon: faCopy,
        size: props.buttonSize,
        variant: "link",
        onClick: () => onCopy(),
    },
    {
        if: !props.workflow.deleted,
        id: "export-button",
        component: "button",
        title: "Export workflow",
        tooltip: "Export workflow",
        icon: faFileExport,
        size: props.buttonSize,
        variant: "link",
        onClick: () => onExport(),
    },
    {
        if: !props.workflow.deleted,
        id: "download-button",
        component: "button",
        title: "Download workflow",
        tooltip: "Download workflow",
        href: downloadUrl.value,
        icon: faDownload,
        size: props.buttonSize,
        variant: "link",
    },
    {
        if: !shared.value && !props.workflow.deleted,
        id: "share-button",
        component: "button",
        title: "Share workflow",
        tooltip: "Share workflow",
        icon: faShareAlt,
        size: props.buttonSize,
        variant: "link",
        onClick: () => onShare(),
    },
    {
        if: props.workflow.deleted,
        id: "restore-button",
        component: "button",
        title: "Restore workflow",
        tooltip: "Restore workflow",
        icon: faTrashRestore,
        size: props.buttonSize,
        variant: "link",
        onClick: () => onRestore(),
    },
    {
        if: !props.published && props.workflow.show_in_tool_panel,
        id: "remove-bookmark-button",
        component: "async",
        title: "Remove bookmark",
        tooltip: "Remove bookmark",
        icon: faStar,
        size: props.buttonSize,
        variant: "link",
        action: () => onToggleBookmark(false),
    },
    {
        if: !props.published && !props.workflow.show_in_tool_panel,
        id: "add-bookmark-button",
        component: "async",
        title: "Add bookmark",
        tooltip: "Add a bookmark. This workflow will appear in the left tool panel.",
        icon: farStar,
        size: props.buttonSize,
        variant: "link",
        action: () => onToggleBookmark(true),
    },
    {
        if: true,
        id: "view-button",
        component: "button",
        title: "View workflow",
        tooltip: "View workflow",
        icon: faEye,
        size: props.buttonSize,
        variant: "link",
        onClick: () => emit("toggleShowPreview", true),
    },
];
</script>

<template>
    <div class="workflow-actions">
        <BDropdown
            v-if="menu"
            id="workflow-actions-dropdown"
            v-b-tooltip.top
            right
            class="show-in-card"
            title="Workflow actions"
            variant="link">
            <BDropdownItem
                v-for="action in actions.filter((a) => a.if)"
                :id="action.id"
                :key="action.id"
                :href="action.href ?? undefined"
                :title="action.tooltip"
                @click="action.component === 'button' ? action.onClick?.() : action.action()">
                <FontAwesomeIcon :icon="action.icon" />
                <span class="ml-1">{{ action.title }}</span>
            </BDropdownItem>
        </BDropdown>

        <div v-else class="d-flex">
            <div v-for="action in actions" :key="action.id">
                <AsyncButton
                    v-if="action.if && action.component === 'async'"
                    :id="action.id"
                    v-b-tooltip.hover
                    :class="{ 'mouse-out': !showControls }"
                    :variant="action.variant"
                    :size="action.size"
                    :title="action.tooltip"
                    :icon="action.icon"
                    :action="action.action" />

                <BButton
                    v-if="action.if && action.component === 'button'"
                    :id="action.id"
                    v-b-tooltip.hover
                    :class="{ 'mouse-out': !showControls }"
                    :variant="action.variant"
                    :size="action.size"
                    :title="action.tooltip"
                    :icon="action.icon"
                    :href="action.href"
                    @click="action.onClick">
                    <FontAwesomeIcon :icon="action.icon" />
                </BButton>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
.workflow-actions {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    justify-content: flex-end;

    .mouse-out {
        opacity: 0.5;
    }
}
</style>
