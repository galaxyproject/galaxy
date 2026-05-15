<script setup lang="ts">
import { faCheckSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import { faClock, faPlus, faTimes, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { GalaxyApi } from "@/api";
import { getGalaxyInstance } from "@/app";
import { useSidebarSelection } from "@/composables/useSidebarSelection";

import { getAgentIcon } from "./agentTypes";
import type { ChatHistoryItem } from "./chatTypes";

import SidebarList from "@/components/Common/SidebarList.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import UtcDate from "@/components/UtcDate.vue";

const router = useRouter();

const chatHistory = ref<ChatHistoryItem[]>([]);
const loading = ref(false);

const {
    selectionMode,
    selectedIds,
    allSelected,
    toggleSelectionMode,
    toggleSelectAll,
    handleSelectionClick,
    pruneAfterDelete,
} = useSidebarSelection(chatHistory, (item) => item.id);

onMounted(() => {
    loadHistory();
});

async function loadHistory() {
    loading.value = true;
    try {
        const { data, error } = await GalaxyApi().GET("/api/chat/history", {
            params: { query: { limit: 50 } },
        });
        if (data && !error) {
            chatHistory.value = data as unknown as ChatHistoryItem[];
        }
    } catch (e) {
        console.error("Failed to load chat history:", e);
    } finally {
        loading.value = false;
    }
}

function handleItemClick(item: ChatHistoryItem, index: number, event: MouseEvent) {
    if (handleSelectionClick(item, index, event)) {
        return;
    }
    const Galaxy = getGalaxyInstance();
    if (Galaxy?.frame?.active) {
        // @ts-ignore - monkeypatched router, second arg is RouterPushOptions
        router.push(`/chatgxy/${item.id}?compact=true`, { title: "ChatGXY" });
    } else {
        router.push(`/chatgxy/${item.id}`);
    }
}

function startNewChat() {
    const Galaxy = getGalaxyInstance();
    if (Galaxy?.frame?.active) {
        // @ts-ignore - monkeypatched router, second arg is RouterPushOptions
        router.push("/chatgxy?compact=true", { title: "ChatGXY" });
    } else {
        router.push("/chatgxy");
    }
}

async function deleteSelected() {
    if (selectedIds.value.size === 0) {
        return;
    }
    const ids = Array.from(selectedIds.value);
    try {
        const { error } = await GalaxyApi().PUT("/api/chat/exchanges/batch/delete", {
            body: { ids },
        });
        if (!error) {
            chatHistory.value = chatHistory.value.filter((item) => !selectedIds.value.has(item.id));
            pruneAfterDelete();
        }
    } catch (e) {
        console.error("Failed to delete exchanges:", e);
    }
}
</script>

<template>
    <ActivityPanel title="ChatGXY" go-to-all-title="Open ChatGXY" href="/chatgxy">
        <template v-slot:header-buttons>
            <button class="btn btn-sm btn-outline-primary" title="New Chat" @click="startNewChat">
                <FontAwesomeIcon :icon="faPlus" fixed-width />
            </button>
            <button
                class="btn btn-sm"
                :class="selectionMode ? 'btn-outline-secondary' : 'btn-outline-danger'"
                :title="selectionMode ? 'Cancel selection' : 'Select chats to delete'"
                @click="toggleSelectionMode">
                <FontAwesomeIcon :icon="selectionMode ? faTimes : faTrash" fixed-width />
            </button>
        </template>

        <div v-if="selectionMode && chatHistory.length > 0" class="selection-toolbar">
            <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events vuejs-accessibility/no-static-element-interactions -->
            <span class="select-all-toggle" @click="toggleSelectAll">
                <FontAwesomeIcon :icon="allSelected ? faCheckSquare : faSquare" fixed-width />
                {{ allSelected ? "Deselect all" : "Select all" }}
            </span>
            <button class="btn btn-sm btn-danger" :disabled="selectedIds.size === 0" @click="deleteSelected">
                Delete {{ selectedIds.size > 0 ? selectedIds.size : "" }}
            </button>
        </div>

        <SidebarList
            :items="chatHistory"
            :is-loading="loading"
            :item-key="(item) => item.id"
            :item-class="(item) => ({ selected: selectedIds.has(item.id) })"
            loading-message="Loading history..."
            empty-message="No chat history yet"
            @select="handleItemClick">
            <template v-slot:item="{ item }">
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
            </template>
        </SidebarList>
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

// SidebarList provides base item hover/cursor styles.
// .selected is applied via itemClass prop on the sidebar-item element,
// which lives inside SidebarList's scoped styles, so we use :deep.
:deep(.sidebar-item.selected) {
    background: rgba($brand-primary, 0.06);
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
