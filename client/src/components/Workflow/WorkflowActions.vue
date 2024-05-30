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
import { storeToRefs } from "pinia";
import { computed, type ComputedRef } from "vue";

import { getGalaxyInstance } from "@/app";
import { deleteWorkflow, updateWorkflow } from "@/components/Workflow/workflows.services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import type { ColorVariant } from "../Common";

import AsyncButton from "@/components/Common/AsyncButton.vue";

library.add(faCaretDown, faExternalLinkAlt, faEye, faFileExport, farStar, faStar, faTrash);

interface Props {
    workflow: any;
    menu?: boolean;
    published?: boolean;
    buttonSize?: "sm" | "md" | "lg";
}

type BaseAction = {
    condition?: boolean;
    class?: string;
    title: string;
    tooltip?: string;
    icon: any;
    href?: string;
    target?: "_blank";
    size: "sm" | "md" | "lg";
    component: "async" | "button";
    variant: ColorVariant | "link";
    onClick?: (e?: MouseEvent | KeyboardEvent) => void;
};

interface AAction extends BaseAction {
    component: "async";
    action: () => Promise<void>;
}

interface BAction extends BaseAction {
    component: "button";
    to?: string;
}

const props = withDefaults(defineProps<Props>(), {
    buttonSize: "sm",
});

const emit = defineEmits<{
    (e: "refreshList", a?: boolean): void;
    (e: "toggleShowPreview", a?: boolean): void;
}>();

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);
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
            condition: !props.workflow.deleted && !props.workflow.show_in_tool_panel,
            class: "workflow-bookmark-button-add",
            component: "async",
            title: "Add bookmarks",
            tooltip: "Add to bookmarks. This workflow will appear in the left tool panel.",
            icon: farStar,
            size: props.buttonSize,
            variant: "link",
            action: () => onToggleBookmark(true),
        },
        {
            condition: !props.workflow.deleted && props.workflow.show_in_tool_panel,
            class: "workflow-bookmark-button-remove",
            component: "async",
            title: "Remove bookmark",
            tooltip: "Remove bookmark",
            icon: faStar,
            size: props.buttonSize,
            variant: "link",
            action: () => onToggleBookmark(false),
        },
        {
            condition: true,
            class: "workflow-view-button",
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
            condition: !isAnonymous.value && !shared.value && !props.workflow.deleted,
            class: "workflow-delete-button",
            component: "button",
            title: "Delete workflow",
            tooltip: "Delete workflow",
            icon: faTrash,
            size: props.buttonSize,
            variant: "link",
            onClick: () => onDelete(),
        },
        {
            condition: sourceType.value.includes("trs"),
            class: "source-trs-button",
            component: "button",
            title: `View on ${props.workflow.source_metadata?.trs_server}`,
            href: `https://dockstore.org/workflows${props.workflow?.source_metadata?.trs_tool_id?.slice(9)}`,
            target: "_blank",
            icon: faExternalLinkAlt,
            size: props.buttonSize,
            variant: "link",
        },
        {
            condition: sourceType.value == "url",
            class: "workflow-view-external-link-button",
            component: "button",
            title: "View external link",
            href: props.workflow.source_metadata?.url,
            target: "_blank",
            icon: faExternalLinkAlt,
            size: props.buttonSize,
            variant: "link",
        },
        {
            condition: !props.workflow.deleted,
            class: "workflow-export-button",
            component: "button",
            title: "Export",
            icon: faFileExport,
            size: props.buttonSize,
            variant: "link",
            to: `/workflows/export?id=${props.workflow.id}`,
        },
    ];
});
</script>

<template>
    <div class="workflow-actions">
        <div v-for="action in actions" :key="action.class">
            <AsyncButton
                v-if="action.condition && action.component === 'async'"
                v-b-tooltip.hover.noninteractive
                :class="action.class"
                class="inline-icon-button mr-1"
                :variant="action.variant"
                :size="action.size"
                :title="action.tooltip"
                :icon="action.icon"
                :action="action.action" />

            <BButton
                v-else-if="action.condition && action.component === 'button'"
                v-b-tooltip.hover.noninteractive
                :class="action.class"
                class="inline-icon-button mr-1"
                :variant="action.variant"
                :size="action.size"
                :title="action.tooltip"
                :href="action.href"
                :to="action.to"
                @click="action.onClick">
                <FontAwesomeIcon :icon="action.icon" fixed-width />
            </BButton>
        </div>

        <BDropdown
            v-b-tooltip.top.noninteractive
            :data-workflow-actions-dropdown="workflow.id"
            right
            no-caret
            class="workflow-actions-dropdown"
            toggle-class="inline-icon-button"
            title="Workflow actions"
            variant="link">
            <template v-slot:button-content>
                <FontAwesomeIcon :icon="faCaretDown" fixed-width />
            </template>

            <BDropdownItem
                v-for="action in menuActions.filter((a) => a.condition).reverse()"
                :key="action.class"
                :class="action.class"
                :href="action.href"
                :title="action.title"
                :target="action.target"
                :to="action.to"
                @click="action.onClick?.()">
                <FontAwesomeIcon :icon="action.icon" fixed-width />
                <span>{{ action.title }}</span>
            </BDropdownItem>
        </BDropdown>
    </div>
</template>

<style scoped lang="scss">
.workflow-actions {
    display: flex;
    align-items: center;
}
</style>
