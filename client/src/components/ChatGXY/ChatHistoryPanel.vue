<script setup lang="ts">
import { faClock, faPlus, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";

import { getAgentIcon } from "./agentTypes";

import LoadingSpan from "@/components/LoadingSpan.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import UtcDate from "@/components/UtcDate.vue";

interface ChatHistoryItem {
    id: string;
    query: string;
    agent_type: string;
    timestamp: string;
}

const router = useRouter();

const chatHistory = ref<ChatHistoryItem[]>([]);
const loading = ref(false);

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

function selectChat(item: ChatHistoryItem) {
    router.push(`/chatgxy/${item.id}`);
}

function startNewChat() {
    router.push("/chatgxy");
}

async function clearHistory() {
    if (!confirm("Are you sure you want to clear your chat history?")) {
        return;
    }
    try {
        const { error } = await GalaxyApi().DELETE("/api/chat/history");
        if (!error) {
            chatHistory.value = [];
        }
    } catch (e) {
        console.error("Failed to clear history:", e);
    }
}
</script>

<template>
    <ActivityPanel title="ChatGXY" go-to-all-title="Open ChatGXY" href="/chatgxy">
        <template v-slot:header-buttons>
            <button class="btn btn-sm btn-outline-primary" title="New Chat" @click="startNewChat">
                <FontAwesomeIcon :icon="faPlus" fixed-width />
            </button>
            <button class="btn btn-sm btn-outline-danger" title="Clear History" @click="clearHistory">
                <FontAwesomeIcon :icon="faTrash" fixed-width />
            </button>
        </template>

        <div v-if="loading" class="text-center p-3">
            <LoadingSpan message="Loading history..." />
        </div>

        <div v-else-if="chatHistory.length === 0" class="text-muted p-3 text-center small">No chat history yet</div>

        <div v-else class="history-list">
            <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events vuejs-accessibility/no-static-element-interactions -->
            <div v-for="item in chatHistory" :key="item.id" class="history-item" @click="selectChat(item)">
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
    </ActivityPanel>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

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
