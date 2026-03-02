<script setup lang="ts">
import { faCheckSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import { faClock, faPlus, faTimes, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { getGalaxyInstance } from "@/app";

import { getAgentIcon } from "./agentTypes";
import type { ChatHistoryItem } from "./chatTypes";

import LoadingSpan from "@/components/LoadingSpan.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import UtcDate from "@/components/UtcDate.vue";

const router = useRouter();

const chatHistory = ref<ChatHistoryItem[]>([]);
const loading = ref(false);
const selectionMode = ref(false);
const selectedIds = ref(new Set<string>());

const allSelected = computed(() => chatHistory.value.length > 0 && selectedIds.value.size === chatHistory.value.length);

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

const lastClickedIndex = ref<number | null>(null);

function handleItemClick(item: ChatHistoryItem, event: MouseEvent) {
    if (selectionMode.value) {
        const currentIndex = chatHistory.value.findIndex((i) => i.id === item.id);
        if (event.shiftKey && lastClickedIndex.value !== null) {
            const start = Math.min(lastClickedIndex.value, currentIndex);
            const end = Math.max(lastClickedIndex.value, currentIndex);
            const next = new Set(selectedIds.value);
            for (let i = start; i <= end; i++) {
                const id = chatHistory.value[i]?.id;
                if (id) {
                    next.add(id);
                }
            }
            selectedIds.value = next;
        } else {
            toggleSelection(item.id);
        }
        lastClickedIndex.value = currentIndex;
    } else {
        const Galaxy = getGalaxyInstance();
        if (Galaxy?.frame?.active) {
            // @ts-ignore - monkeypatched router, second arg is RouterPushOptions
            router.push(`/chatgxy/${item.id}?compact=true`, { title: "ChatGXY" });
        } else {
            router.push(`/chatgxy/${item.id}`);
        }
    }
}

function toggleSelectionMode() {
    selectionMode.value = !selectionMode.value;
    if (!selectionMode.value) {
        selectedIds.value.clear();
    }
}

function toggleSelection(id: string) {
    const next = new Set(selectedIds.value);
    if (next.has(id)) {
        next.delete(id);
    } else {
        next.add(id);
    }
    selectedIds.value = next;
}

function toggleSelectAll() {
    if (allSelected.value) {
        selectedIds.value = new Set();
    } else {
        selectedIds.value = new Set(chatHistory.value.map((item) => item.id));
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
            selectedIds.value = new Set();
            if (chatHistory.value.length === 0) {
                selectionMode.value = false;
            }
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

        <div v-if="loading" class="text-center p-3">
            <LoadingSpan message="Loading history..." />
        </div>

        <div v-else-if="chatHistory.length === 0" class="text-muted p-3 text-center small">No chat history yet</div>

        <template v-else>
            <div v-if="selectionMode" class="selection-toolbar">
                <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events vuejs-accessibility/no-static-element-interactions -->
                <span class="select-all-toggle" @click="toggleSelectAll">
                    <FontAwesomeIcon :icon="allSelected ? faCheckSquare : faSquare" fixed-width />
                    {{ allSelected ? "Deselect all" : "Select all" }}
                </span>
                <button class="btn btn-sm btn-danger" :disabled="selectedIds.size === 0" @click="deleteSelected">
                    Delete {{ selectedIds.size > 0 ? selectedIds.size : "" }}
                </button>
            </div>

            <div class="history-list">
                <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events vuejs-accessibility/no-static-element-interactions -->
                <div
                    v-for="item in chatHistory"
                    :key="item.id"
                    class="history-item"
                    :class="{ selected: selectedIds.has(item.id) }"
                    @click="handleItemClick(item, $event)">
                    <div class="history-row">
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
                </div>
            </div>
        </template>
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

.history-list {
    flex: 1;
    overflow-y: auto;
}

.history-item {
    padding: 0.5rem 0.25rem;
    border-bottom: 1px solid darken($panel-bg-color, 5%);
    cursor: pointer;
    transition: background-color 0.15s;
    border-radius: $border-radius-base;

    &:hover {
        background: darken($panel-bg-color, 3%);
    }

    &.selected {
        background: rgba($brand-primary, 0.06);
    }

    .history-row {
        display: flex;
        align-items: flex-start;
        gap: 0.375rem;
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
}
</style>
