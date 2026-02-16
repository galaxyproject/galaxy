<script setup lang="ts">
import { faCheckSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import { faClock, faComments, faTimes, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, watch } from "vue";

import type { components } from "@/api";
import { useSidebarSelection } from "@/composables/useSidebarSelection";

import SidebarList from "@/components/Common/SidebarList.vue";
import UtcDate from "@/components/UtcDate.vue";

type ChatHistoryItem = components["schemas"]["ChatHistoryItemResponse"];

const props = defineProps<{
    items: ChatHistoryItem[];
    isLoading: boolean;
    error: string | null;
    activeExchangeId: string | null;
}>();

const emit = defineEmits<{
    (e: "select", item: ChatHistoryItem): void;
    (e: "delete", ids: string[]): void;
    (e: "dismiss-error"): void;
}>();

const itemsRef = computed(() => props.items);

const {
    selectionMode,
    selectedIds,
    allSelected,
    toggleSelectionMode,
    toggleSelectAll,
    handleSelectionClick,
    pruneAfterDelete,
} = useSidebarSelection(itemsRef, (item) => item.id);

function itemKey(item: ChatHistoryItem): string {
    return item.id;
}

function itemClass(item: ChatHistoryItem): Record<string, boolean> {
    return {
        active: !selectionMode.value && item.id === props.activeExchangeId,
        selected: selectedIds.value.has(item.id),
    };
}

function onSelect(item: ChatHistoryItem, index: number, event: MouseEvent) {
    if (handleSelectionClick(item, index, event)) {
        return;
    }
    emit("select", item);
}

function deleteSelected() {
    if (selectedIds.value.size === 0) {
        return;
    }
    emit("delete", Array.from(selectedIds.value));
}

// Items are owned by the parent (store) and removed asynchronously after
// the "delete" emit. Prune stale selections once the prop actually updates.
watch(itemsRef, () => {
    if (selectionMode.value) {
        pruneAfterDelete();
    }
});

defineExpose({ selectionMode, toggleSelectionMode });
</script>

<template>
    <div class="page-chat-history-list" data-description="page chat history list">
        <div class="history-toolbar d-flex align-items-center justify-content-between px-2 py-1 border-bottom">
            <span class="toolbar-label">History</span>
            <button
                class="btn btn-sm"
                :class="selectionMode ? 'btn-outline-secondary' : 'btn-outline-danger'"
                :title="selectionMode ? 'Cancel selection' : 'Select chats to delete'"
                data-description="toggle selection button"
                @click="toggleSelectionMode">
                <FontAwesomeIcon :icon="selectionMode ? faTimes : faTrash" fixed-width />
            </button>
        </div>

        <div v-if="selectionMode && items.length > 0" class="selection-toolbar">
            <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events vuejs-accessibility/no-static-element-interactions -->
            <span class="select-all-toggle" @click="toggleSelectAll">
                <FontAwesomeIcon :icon="allSelected ? faCheckSquare : faSquare" fixed-width />
                {{ allSelected ? "Deselect all" : "Select all" }}
            </span>
            <button
                class="btn btn-sm btn-danger"
                :disabled="selectedIds.size === 0"
                data-description="delete selected button"
                @click="deleteSelected">
                Delete {{ selectedIds.size > 0 ? selectedIds.size : "" }}
            </button>
        </div>

        <BAlert
            v-if="props.error"
            variant="danger"
            dismissible
            show
            class="m-2 mb-0"
            data-description="chat history error"
            @dismissed="emit('dismiss-error')">
            {{ props.error }}
        </BAlert>

        <SidebarList
            :items="items"
            :is-loading="isLoading"
            loading-message="Loading history..."
            empty-message="No conversations yet."
            :item-key="itemKey"
            :item-class="itemClass"
            @select="onSelect">
            <template v-slot:item="{ item }">
                <span v-if="selectionMode" class="history-checkbox">
                    <FontAwesomeIcon :icon="selectedIds.has(item.id) ? faCheckSquare : faSquare" fixed-width />
                </span>
                <div class="history-content">
                    <div class="history-query">{{ item.query }}</div>
                    <div class="history-meta">
                        <span v-if="item.message_count" class="history-messages">
                            <FontAwesomeIcon :icon="faComments" fixed-width />
                            {{ item.message_count }}
                        </span>
                        <span v-if="item.timestamp" class="history-time">
                            <FontAwesomeIcon :icon="faClock" fixed-width />
                            <UtcDate :date="item.timestamp" mode="elapsed" />
                        </span>
                    </div>
                </div>
            </template>
        </SidebarList>
    </div>
</template>

<style scoped>
.page-chat-history-list {
    max-height: 100%;
    overflow-y: auto;
}

.history-toolbar {
    font-size: 0.75rem;
    font-weight: 600;
}

.toolbar-label {
    text-transform: uppercase;
    letter-spacing: 0.025em;
    color: var(--text-muted, #6c757d);
}

.selection-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.375rem 0.5rem;
    border-bottom: 1px solid var(--border-color, #dee2e6);
    font-size: 0.75rem;
}

.select-all-toggle {
    cursor: pointer;
    color: var(--text-muted, #6c757d);
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.select-all-toggle:hover {
    color: var(--text-color, #212529);
}

:deep(.sidebar-item.active) {
    background: rgba(var(--brand-primary-rgb, 0, 123, 255), 0.08);
    border-left: 3px solid var(--brand-primary, #007bff);
    padding-left: calc(0.5rem - 3px);
}

:deep(.sidebar-item.selected) {
    background: rgba(var(--brand-primary-rgb, 0, 123, 255), 0.06);
}

.history-checkbox {
    flex-shrink: 0;
    color: var(--text-muted, #6c757d);
    padding-top: 0.1rem;
}

.history-content {
    flex: 1;
    min-width: 0;
}

.history-query {
    font-size: 0.8rem;
    color: var(--text-color, #212529);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 0.2rem;
}

.history-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.7rem;
    color: var(--text-muted, #6c757d);
}

.history-messages {
    display: flex;
    align-items: center;
    gap: 0.2rem;
}

.history-time {
    display: flex;
    align-items: center;
    gap: 0.2rem;
}
</style>
