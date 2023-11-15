<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import {
    faCaretDown,
    faExternalLinkAlt,
    faEye,
    faFileExport,
    faStar,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, type ComputedRef } from "vue";
import { useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import { deleteWorkflow, updateWorkflow } from "@/components/Workflow/workflows.services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import AsyncButton from "@/components/Common/AsyncButton.vue";

library.add(faCaretDown, faExternalLinkAlt, faEye, faFileExport, farStar, faStar, faTrash);

interface Props {
    workflow: any;
    menu?: boolean;
    published?: boolean;
    buttonSize?: "sm" | "md" | "lg";
}

type BaseAction = {
    if?: boolean;
    id: string;
    title: string;
    tooltip?: string;
    icon: any;
    href?: string;
    target?: "_blank";
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

const shared = computed(() => {
    if (userStore.currentUser) {
        return userStore.currentUser.username !== props.workflow.owner;
    } else {
        return false;
    }
});
const sourceType = computed(() => {
    if (props.workflow.source_metadata?.url) {
        return "url";
    } else if (props.workflow.source_metadata?.trs_server) {
        return `trs_${props.workflow.source_metadata?.trs_server}`;
    } else {
        return "";
    }
});

function onExport() {
    router.push(`/workflows/export?id=${props.workflow.id}`);
}

async function onToggleBookmark(checked: boolean) {
    await updateWorkflow(props.workflow.id, {
        show_in_tool_panel: checked,
    });
    emit("refreshList", true);
    Toast.info(`Workflow ${checked ? "added to" : "removed from"} bookmarks`);
    if (checked) {
        getGalaxyInstance().config.stored_workflow_menu_entries.push({
            id: props.workflow.id,
            name: props.workflow.name,
        });
    } else {
        const indexToRemove = getGalaxyInstance().config.stored_workflow_menu_entries.findIndex(
            (w: any) => w.id === props.workflow.id
        );
        getGalaxyInstance().config.stored_workflow_menu_entries.splice(indexToRemove, 1);
    }
}

async function onDelete() {
    const confirmed = await confirm("Are you sure you want to delete this workflow?", {
        title: "Delete workflow",
        okTitle: "Delete",
        okVariant: "danger",
    });

    if (confirmed) {
        await deleteWorkflow(props.workflow.id);
        emit("refreshList", true);
        Toast.info("Workflow deleted");
    }
}

const actions: ComputedRef<(AAction | BAction)[]> = computed(() => {
    return [
        {
            if: !shared.value && !props.workflow.show_in_tool_panel,
            id: "workflow-bookmark-button",
            component: "async",
            title: "Add bookmarks",
            tooltip: "Add to bookmarks. This workflow will appear in the left tool panel.",
            icon: farStar,
            size: props.buttonSize,
            variant: "link",
            action: () => onToggleBookmark(true),
        },
        {
            if: !shared.value && props.workflow.show_in_tool_panel,
            id: "workflow-bookmark-button",
            component: "async",
            title: "Remove bookmark",
            tooltip: "Remove bookmark",
            icon: faStar,
            size: props.buttonSize,
            variant: "link",
            action: () => onToggleBookmark(false),
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
});

const menuActions: ComputedRef<BAction[]> = computed(() => {
    return [
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
            if: sourceType.value.includes("trs"),
            id: "source-trs-button",
            component: "button",
            title: `View on ${props.workflow.source_metadata?.trs_server}`,
            href: `https://dockstore.org/workflows${props.workflow?.source_metadata?.trs_tool_id?.slice(9)}`,
            target: "_blank",
            icon: faExternalLinkAlt,
            size: props.buttonSize,
            variant: "link",
        },
        {
            if: sourceType.value == "url",
            id: "source-url-button",
            component: "button",
            title: "View external link",
            href: props.workflow.source_metadata?.url,
            target: "_blank",
            icon: faExternalLinkAlt,
            size: props.buttonSize,
            variant: "link",
        },
        {
            if: !props.workflow.deleted,
            id: "export-button",
            component: "button",
            title: "Export",
            icon: faFileExport,
            size: props.buttonSize,
            variant: "link",
            onClick: () => onExport(),
        },
    ];
});
</script>

<template>
    <div class="workflow-actions flex-gapx-1">
        <div v-for="action in actions" :key="action.id">
            <AsyncButton
                v-if="action.if && action.component === 'async'"
                :id="action.id"
                v-b-tooltip.hover
                class="inline-icon-button"
                :variant="action.variant"
                :size="action.size"
                :title="action.tooltip"
                :icon="action.icon"
                :action="action.action" />

            <BButton
                v-if="action.if && action.component === 'button'"
                :id="action.id"
                v-b-tooltip.hover
                class="inline-icon-button"
                :variant="action.variant"
                :size="action.size"
                :title="action.tooltip"
                :href="action.href"
                @click="action.onClick">
                <FontAwesomeIcon :icon="action.icon" />
            </BButton>
        </div>

        <BDropdown
            id="workflow-actions-dropdown"
            v-b-tooltip.top
            :data-workflow-actions-dropdown="workflow.id"
            right
            no-caret
            class="show-in-card"
            toggle-class="inline-icon-button"
            title="Workflow actions"
            variant="link">
            <template v-slot:button-content>
                <FontAwesomeIcon :icon="faCaretDown" fixed-width />
            </template>

            <BDropdownItem
                v-for="action in menuActions.filter((a) => a.if).reverse()"
                :id="action.id"
                :key="action.id"
                :href="action.href ?? undefined"
                :title="action.title"
                :target="action.target"
                @click="action.onClick?.()">
                <FontAwesomeIcon :icon="action.icon" />
                <span>{{ action.title }}</span>
            </BDropdownItem>
        </BDropdown>
    </div>
</template>

<style scoped lang="scss">
.workflow-actions {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    justify-content: flex-end;
}
</style>
