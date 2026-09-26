<script setup lang="ts">
import { faCheckSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import { faClock, faPlus, faTimes, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";
import { useActiveContext } from "@/composables/useActiveContext";
import { useSidebarSelection } from "@/composables/useSidebarSelection";
import { useChatStore } from "@/stores/chatStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { getAgentIcon } from "./agentTypes";
import type { ChatHistoryItem } from "./chatTypes";
import { useStartNewChat } from "./useStartNewChat";

import GButton from "../BaseComponents/GButton.vue";
import ChatModeSelector from "./ChatModeSelector.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";
import UtcDate from "@/components/UtcDate.vue";

const { confirm } = useConfirmDialog();
const Toast = useToast();
const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const { activeContext } = useActiveContext();

const notebookPageId = computed(() => {
    const ctx = activeContext.value;
    return ctx?.contextType === "notebook" ? ctx.pageId : undefined;
});

const newChat = useStartNewChat();

const { chatHistory, loading } = storeToRefs(chatStore);

const {
    selectionMode,
    selectedIds,
    allSelected,
    toggleSelectionMode,
    toggleSelectAll,
    handleSelectionClick,
    pruneAfterDelete,
} = useSidebarSelection(chatHistory, (item) => item.id);

const currentExchangeId = computed(() => {
    if (chatStore.isCenterMode) {
        return route.params["exchangeId"] || null;
    } else {
        return chatStore.activeChatId;
    }
});

watch(
    notebookPageId,
    async (pageId) => {
        try {
            await chatStore.loadHistory(pageId);
        } catch (e) {
            Toast.error(errorMessageAsString(e), "Failed to load chat history");
        }
    },
    { immediate: true },
);

function handleItemClick(item: ChatHistoryItem, index: number, event: MouseEvent) {
    if (handleSelectionClick(item, index, event)) {
        return;
    }
    if (chatStore.isCenterMode) {
        router.push(`/galaxyai/${item.id}`);
    } else {
        chatStore.showChat(item.id);
    }
}

function startNewChat() {
    newChat(chatStore.isCenterMode);
}

async function deleteSelected() {
    if (selectedIds.value.size === 0) {
        return;
    }

    const confirmed = await confirm(
        `Are you sure you want to delete the ${selectedIds.value.size} selected conversation(s)?`,
        {
            title: "Delete Conversations",
            okText: "Delete",
            okIcon: faTrash,
            okColor: "red",
        },
    );
    if (confirmed) {
        const deletedIds = new Set(selectedIds.value);
        const routedChatId = currentExchangeId.value;
        try {
            await chatStore.deleteChatsByIds(deletedIds);
            pruneAfterDelete();
            // In center mode the visible chat is driven by the route, not activeChatId, so if we
            // just deleted the one on screen, move to a fresh chat rather than a dead route.
            if (chatStore.isCenterMode && routedChatId && deletedIds.has(routedChatId)) {
                router.push("/galaxyai/new");
            }
        } catch (e) {
            Toast.error(errorMessageAsString(e, "Failed to delete conversations."), "Error deleting conversations");
        }
    }
}
</script>

<template>
    <ActivityPanel title="GalaxyAI">
        <template v-slot:header-buttons>
            <GButton color="blue" transparent size="small" title="New Chat" @click="startNewChat">
                <FontAwesomeIcon :icon="faPlus" fixed-width />
            </GButton>
            <GButton
                :disabled="chatHistory.length === 0"
                transparent
                size="small"
                :pressed="selectionMode"
                :title="selectionMode ? 'Cancel selection' : 'Select chats to delete'"
                @click="toggleSelectionMode">
                <FontAwesomeIcon :icon="selectionMode ? faTimes : faTrash" fixed-width />
            </GButton>
        </template>

        <template v-slot:header>
            <ChatModeSelector class="pt-1" />
        </template>

        <div v-if="selectionMode && chatHistory.length > 0" class="selection-toolbar">
            <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events vuejs-accessibility/no-static-element-interactions -->
            <span class="select-all-toggle" @click="toggleSelectAll">
                <FontAwesomeIcon :icon="allSelected ? faCheckSquare : faSquare" fixed-width />
                {{ allSelected ? "Deselect all" : "Select all" }}
            </span>
            <GButton
                data-description="delete selected chats"
                :disabled="selectedIds.size === 0"
                size="small"
                @click="deleteSelected">
                <FontAwesomeIcon :icon="faTrash" fixed-width />
                Delete {{ selectedIds.size > 0 ? selectedIds.size : "" }}
            </GButton>
        </div>

        <ScrollList
            :prop-items="chatHistory"
            :prop-busy="loading"
            :prop-total-count="chatHistory.length"
            :item-key="(item) => item.id"
            load-disabled
            in-panel
            name="chat"
            name-plural="chats">
            <template v-slot:item="{ item, index }">
                <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events vuejs-accessibility/no-static-element-interactions -->
                <div
                    class="chat-history-item d-flex align-items-start p-2 border-bottom unselectable"
                    :class="{ selected: selectedIds.has(item.id), current: item.id === currentExchangeId }"
                    role="button"
                    tabindex="0"
                    @click="(event) => handleItemClick(item, index, event)">
                    <span v-if="selectionMode" class="history-checkbox">
                        <FontAwesomeIcon :icon="selectedIds.has(item.id) ? faCheckSquare : faSquare" fixed-width />
                    </span>
                    <div class="history-content">
                        <div class="history-query">{{ item.query }}</div>
                        <div class="history-meta">
                            <span class="history-agent">
                                <FontAwesomeIcon :icon="getAgentIcon(item.agent_type)" fixed-width />
                            </span>
                            <span class="history-time">
                                <FontAwesomeIcon :icon="faClock" class="mr-1" />
                                <UtcDate :date="item.timestamp" mode="elapsed" />
                            </span>
                        </div>
                    </div>
                </div>
            </template>
        </ScrollList>
    </ActivityPanel>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.selection-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.375rem 0.5rem;
    border-bottom: 1px solid darken($panel-bg-color, 5%);
    font-size: 0.75rem;
}

.select-all-toggle {
    cursor: pointer;
    color: $text-muted;
    display: flex;
    align-items: center;
    gap: 0.25rem;

    &:hover {
        color: $text-color;
    }
}

:deep(.chat-history-item) {
    cursor: pointer;
    &:hover {
        background: var(--color-grey-200) !important;
    }
}
:deep(.chat-history-item.selected) {
    background: var(--color-blue-200);
}
:deep(.chat-history-item.current) {
    border-left: 0.25rem solid $brand-primary;
}

.history-checkbox {
    flex-shrink: 0;
    color: $text-muted;
    padding-top: 0.1rem;
}

.history-content {
    flex: 1;
    min-width: 0;
}

.history-query {
    font-size: 0.8rem;
    color: $text-color;
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
    color: $text-light;

    .history-agent {
        color: $brand-primary;
    }

    .history-time {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
}
</style>
