<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import {
    faCaretDown,
    faExternalLinkAlt,
    faEye,
    faFileExport,
    faSpinner,
    faStar,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { getGalaxyInstance } from "@/app";
import { deleteWorkflow, updateWorkflow } from "@/components/Workflow/workflows.services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

library.add(farStar, faCaretDown, faExternalLinkAlt, faEye, faFileExport, faSpinner, faStar, faTrash);

interface Props {
    workflow: any;
    published?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    published: false,
});

const emit = defineEmits<{
    (e: "refreshList", a?: boolean): void;
}>();

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const { confirm } = useConfirmDialog();

const bookmarkLoading = ref(false);

const shared = computed(() => {
    return !userStore.matchesCurrentUsername(props.workflow.owner);
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
    try {
        bookmarkLoading.value = true;

        await updateWorkflow(props.workflow.id, {
            show_in_tool_panel: checked,
        });

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
    } catch (error) {
        Toast.error("Failed to update workflow bookmark status");
    } finally {
        emit("refreshList", true);
        bookmarkLoading.value = false;
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
</script>

<template>
    <div class="workflow-actions">
        <BButtonGroup>
            <BButton
                v-if="!props.workflow.deleted && !props.workflow.show_in_tool_panel"
                v-b-tooltip.hover.noninteractive
                class="workflow-bookmark-button-add inline-icon-button"
                variant="link"
                title="Add to bookmarks"
                tooltip="Add to bookmarks. This workflow will appear in the left tool panel."
                size="sm"
                @click="onToggleBookmark(true)">
                <FontAwesomeIcon v-if="!bookmarkLoading" :icon="farStar" fixed-width />
                <FontAwesomeIcon v-else :icon="faSpinner" spin fixed-width />
            </BButton>
            <BButton
                v-else-if="!props.workflow.deleted && props.workflow.show_in_tool_panel"
                v-b-tooltip.hover.noninteractive
                class="workflow-bookmark-button-remove inline-icon-button"
                variant="link"
                title="Remove bookmark"
                size="sm"
                @click="onToggleBookmark(false)">
                <FontAwesomeIcon v-if="!bookmarkLoading" :icon="faStar" fixed-width />
                <FontAwesomeIcon v-else :icon="faSpinner" spin fixed-width />
            </BButton>

            <BDropdown
                v-b-tooltip.top.noninteractive
                :data-workflow-actions-dropdown="workflow.id"
                right
                no-caret
                class="workflow-actions-dropdown"
                title="Workflow actions"
                toggle-class="inline-icon-button"
                variant="link">
                <template v-slot:button-content>
                    <FontAwesomeIcon :icon="faCaretDown" fixed-width />
                </template>

                <BDropdownItem
                    v-if="!isAnonymous && !shared && !props.workflow.deleted"
                    class="workflow-delete-button"
                    title="Delete workflow"
                    size="sm"
                    variant="link"
                    @click="onDelete">
                    <FontAwesomeIcon :icon="faTrash" fixed-width />
                    <span>Delete</span>
                </BDropdownItem>

                <BDropdownItem
                    v-if="sourceType.includes('trs')"
                    class="source-trs-button"
                    :title="`View on ${props.workflow.source_metadata?.trs_server}`"
                    size="sm"
                    variant="link"
                    :href="`https://dockstore.org/workflows${props.workflow?.source_metadata?.trs_tool_id?.slice(9)}`"
                    target="_blank">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                    <span>View on Dockstore</span>
                </BDropdownItem>

                <BDropdownItem
                    v-if="sourceType == 'url'"
                    class="workflow-view-external-link-button"
                    title="View external link"
                    size="sm"
                    variant="link"
                    :href="props.workflow.source_metadata?.url"
                    target="_blank">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                    <span>View external link</span>
                </BDropdownItem>

                <BDropdownItem
                    v-if="!props.workflow.deleted"
                    class="workflow-export-button"
                    title="Export"
                    size="sm"
                    variant="link"
                    :to="`/workflows/export?id=${props.workflow.id}`">
                    <FontAwesomeIcon :icon="faFileExport" fixed-width />
                    <span>Export</span>
                </BDropdownItem>
            </BDropdown>
        </BButtonGroup>
    </div>
</template>

<style scoped lang="scss">
.workflow-actions {
    display: flex;
    align-items: center;
}
</style>
