<script setup lang="ts">
import { faClock, faHistory, faMagic, faPlus, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BSkeleton } from "bootstrap-vue";
import { nextTick, onMounted, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { type AgentResponse, type ChatMessage, useAgentActions } from "@/composables/agentActions";
import { useMarkdown } from "@/composables/markdown";
import { errorMessageAsString } from "@/utils/simple-error";

import { getAgentIcon, getAgentLabel } from "./ChatGXY/agentTypes";
import { generateId, scrollToBottom } from "./ChatGXY/chatUtils";

import ChatInput from "./ChatGXY/ChatInput.vue";
import ChatMessageCell from "./ChatGXY/ChatMessageCell.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

interface ChatHistoryItem {
    id: number;
    query: string;
    response: string;
    agent_type: string;
    agent_response?: AgentResponse;
    timestamp: string;
    feedback?: number | null;
}

const query = ref("");
const messages = ref<ChatMessage[]>([]);
const errorMessage = ref("");
const busy = ref(false);
const chatContainer = ref<HTMLElement>();
const selectedAgentType = ref("auto");
const showHistory = ref(false);
const chatHistory = ref<ChatHistoryItem[]>([]);
const loadingHistory = ref(false);
const currentChatId = ref<number | null>(null);
const hasLoadedInitialChat = ref(false);

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, removeNewlinesAfterList: true });
const { processingAction, handleAction } = useAgentActions();

onMounted(async () => {
    await loadLatestChat();

    if (!hasLoadedInitialChat.value) {
        messages.value.push({
            id: generateId(),
            role: "assistant",
            content:
                "👋 Welcome to ChatGXY! I can help you with:\n\n" +
                "• **Finding the right tools** for your analysis\n" +
                "• **Debugging errors** in your workflows\n" +
                "• **Optimizing performance** of your pipelines\n" +
                "• **Checking data quality** issues\n\n" +
                "Just ask me anything about Galaxy and I'll route your question to the right specialist!",
            timestamp: new Date(),
            agentType: "router",
            confidence: "high",
            feedback: null,
            isSystemMessage: true,
        });
    }
});

async function submitQuery() {
    if (!query.value.trim()) {
        return;
    }

    const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content: query.value,
        timestamp: new Date(),
        feedback: null,
    };

    messages.value.push(userMessage);
    const currentQuery = query.value;
    query.value = "";

    await nextTick();
    scrollToBottom(chatContainer.value);

    busy.value = true;
    errorMessage.value = "";

    try {
        const { data, error } = await GalaxyApi().POST("/api/chat", {
            params: {
                query: {
                    agent_type: selectedAgentType.value,
                },
            },
            body: {
                query: currentQuery,
                context: null,
                exchange_id: currentChatId.value,
            },
        });

        if (error) {
            errorMessage.value = errorMessageAsString(error, "Failed to get response from ChatGXY.");
            const errorMsg: ChatMessage = {
                id: generateId(),
                role: "assistant",
                content: `❌ Error: ${errorMessage.value}`,
                timestamp: new Date(),
                agentType: selectedAgentType.value,
                confidence: "low",
                feedback: null,
            };
            messages.value.push(errorMsg);

            await nextTick();
            scrollToBottom(chatContainer.value);
        } else if (data) {
            const agentResponse = data.agent_response as AgentResponse | undefined;
            const content = data.response || "No response received";

            if (data.exchange_id) {
                currentChatId.value = data.exchange_id;
            }

            const assistantMessage: ChatMessage = {
                id: generateId(),
                role: "assistant",
                content: content,
                timestamp: new Date(),
                agentType:
                    agentResponse?.agent_type ||
                    (selectedAgentType.value === "auto" ? "router" : selectedAgentType.value),
                confidence: agentResponse?.confidence || "medium",
                feedback: null,
                agentResponse: agentResponse,
                suggestions: agentResponse?.suggestions || [],
            };
            messages.value.push(assistantMessage);

            await nextTick();
            scrollToBottom(chatContainer.value);
        }
    } catch (e) {
        errorMessage.value = `Unexpected error: ${e}`;
        const errorMsg: ChatMessage = {
            id: generateId(),
            role: "assistant",
            content: `❌ Unexpected error occurred. Please try again.`,
            timestamp: new Date(),
            agentType: selectedAgentType.value,
            confidence: "low",
            feedback: null,
        };
        messages.value.push(errorMsg);

        await nextTick();
        scrollToBottom(chatContainer.value);
    } finally {
        busy.value = false;
        await nextTick();
        scrollToBottom(chatContainer.value);
    }
}

watch(busy, (isBusy) => {
    if (isBusy) {
        nextTick(() => scrollToBottom(chatContainer.value));
    }
});

async function sendFeedback(messageId: string, value: "up" | "down") {
    const message = messages.value.find((m) => m.id === messageId);
    if (message) {
        message.feedback = value;

        if (currentChatId.value) {
            try {
                const feedbackValue = value === "up" ? 1 : 0;
                const { error } = await GalaxyApi().PUT("/api/chat/exchange/{exchange_id}/feedback", {
                    params: {
                        path: { exchange_id: currentChatId.value },
                    },
                    body: feedbackValue,
                });

                if (error) {
                    console.error("Failed to save feedback:", error);
                    message.feedback = null;
                }
            } catch (e) {
                console.error("Failed to save feedback:", e);
                message.feedback = null;
            }
        }
    }
}

async function loadChatHistory() {
    loadingHistory.value = true;
    try {
        const { data, error } = await GalaxyApi().GET("/api/chat/history", {
            params: {
                query: { limit: 50 },
            },
        });

        if (data && !error) {
            chatHistory.value = data as unknown as ChatHistoryItem[];
        }
    } catch (e) {
        console.error("Failed to load chat history:", e);
    } finally {
        loadingHistory.value = false;
    }
}

async function clearHistory() {
    if (!confirm("Are you sure you want to clear your chat history?")) {
        return;
    }

    try {
        const { data, error } = await GalaxyApi().DELETE("/api/chat/history");
        if (!error && data) {
            console.log("Clear history response:", data);
            chatHistory.value = [];
            if (currentChatId.value) {
                startNewChat();
            }
        } else if (error) {
            console.error("Failed to clear history - API error:", error);
            alert("Failed to clear history. Please try again.");
        }
    } catch (e) {
        console.error("Failed to clear history - exception:", e);
        alert("Failed to clear history. Please try again.");
    }
}

async function loadPreviousChat(item: ChatHistoryItem) {
    try {
        const { data: fullConversation } = await GalaxyApi().GET(`/api/chat/exchange/{exchange_id}/messages`, {
            params: {
                path: {
                    exchange_id: item.id,
                },
            },
        });

        if (fullConversation && fullConversation.length > 0) {
            messages.value = [];

            fullConversation.forEach((msg: any, index: number) => {
                const message: ChatMessage = {
                    id: `hist-${msg.role}-${item.id}-${index}`,
                    role: msg.role as "user" | "assistant",
                    content: msg.content,
                    timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
                    feedback: null,
                };

                if (msg.role === "assistant") {
                    message.agentType = msg.agent_type;
                    message.confidence = msg.agent_response?.confidence || "medium";
                    message.feedback = msg.feedback === 1 ? "up" : msg.feedback === 0 ? "down" : null;

                    if (msg.agent_response) {
                        message.agentResponse = msg.agent_response;
                        message.suggestions = msg.agent_response.suggestions || [];
                    }
                }

                messages.value.push(message);
            });
        } else {
            loadSingleMessageFallback(item);
        }

        currentChatId.value = item.id;
        showHistory.value = false;
        nextTick(() => scrollToBottom(chatContainer.value));
    } catch (error) {
        console.error("Error loading full conversation:", error);
        loadSingleMessageFallback(item);
    }
}

function loadSingleMessageFallback(item: ChatHistoryItem) {
    const userMessage: ChatMessage = {
        id: `hist-user-${item.id}`,
        role: "user",
        content: item.query,
        timestamp: new Date(item.timestamp),
        feedback: null,
    };

    const assistantMessage: ChatMessage = {
        id: `hist-assistant-${item.id}`,
        role: "assistant",
        content: item.response,
        timestamp: new Date(item.timestamp),
        agentType: item.agent_type,
        confidence: item.agent_response?.confidence || "medium",
        feedback: item.feedback === 1 ? "up" : item.feedback === 0 ? "down" : null,
    };

    if (item.agent_response) {
        assistantMessage.agentResponse = item.agent_response;
        assistantMessage.suggestions = item.agent_response.suggestions || [];
    }

    messages.value = [userMessage, assistantMessage];
    currentChatId.value = item.id;
    showHistory.value = false;
    nextTick(() => scrollToBottom(chatContainer.value));
}

async function loadLatestChat() {
    try {
        const { data, error } = await GalaxyApi().GET("/api/chat/history", {
            params: {
                query: { limit: 1 },
            },
        });

        if (data && !error && data.length > 0) {
            const latestChat = data[0] as unknown as ChatHistoryItem;
            await loadPreviousChat(latestChat);
            hasLoadedInitialChat.value = true;
        }
    } catch (e) {
        console.error("Failed to load latest chat:", e);
    }
}

function startNewChat() {
    messages.value = [
        {
            id: generateId(),
            role: "assistant",
            content: "👋 Starting a new conversation! How can I help you today?",
            timestamp: new Date(),
            agentType: "router",
            confidence: "high",
            feedback: null,
            isSystemMessage: true,
        },
    ];
    currentChatId.value = null;
    query.value = "";
    errorMessage.value = "";
}

function toggleHistory() {
    showHistory.value = !showHistory.value;
    if (showHistory.value && chatHistory.value.length === 0) {
        loadChatHistory();
    }
}
</script>

<template>
    <div class="chatgxy-container">
        <div class="chatgxy-header">
            <Heading h2 :icon="faMagic" size="lg">
                <span>ChatGXY</span>
            </Heading>
            <div class="header-actions">
                <button class="btn btn-sm btn-outline-primary" title="Start New Chat" @click="startNewChat">
                    <FontAwesomeIcon :icon="faPlus" fixed-width />
                    New
                </button>
                <button
                    class="btn btn-sm"
                    :class="showHistory ? 'btn-primary' : 'btn-outline-primary'"
                    :title="showHistory ? 'Hide History' : 'Show History'"
                    @click="toggleHistory">
                    <FontAwesomeIcon :icon="faHistory" fixed-width />
                </button>
            </div>
        </div>

        <div class="chatgxy-body">
            <!-- History Sidebar -->
            <div v-if="showHistory" class="history-sidebar">
                <div class="history-header">
                    <h5>Chat History</h5>
                    <button class="btn btn-sm btn-link text-danger p-0" title="Clear History" @click="clearHistory">
                        <FontAwesomeIcon :icon="faTrash" />
                    </button>
                </div>

                <div v-if="loadingHistory" class="text-center p-3">
                    <LoadingSpan message="Loading history..." />
                </div>

                <div v-else-if="chatHistory.length === 0" class="text-muted p-3 text-center">No chat history yet</div>

                <div v-else class="history-list">
                    <div
                        v-for="item in chatHistory"
                        :key="item.id"
                        class="history-item"
                        @click="() => loadPreviousChat(item)">
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

            <!-- Main Chat Area -->
            <div ref="chatContainer" class="chat-messages flex-grow-1">
                <ChatMessageCell
                    v-for="message in messages"
                    :key="message.id"
                    :message="message"
                    :render-markdown="renderMarkdown"
                    :processing-action="processingAction"
                    @feedback="sendFeedback"
                    @handle-action="handleAction" />

                <!-- Loading state -->
                <div v-if="busy" class="notebook-cell response-cell loading-cell">
                    <div class="cell-label">
                        <FontAwesomeIcon :icon="getAgentIcon(selectedAgentType)" fixed-width />
                        <span>{{ getAgentLabel(selectedAgentType) }}</span>
                    </div>
                    <div class="cell-content">
                        <BSkeleton animation="wave" width="85%" />
                        <BSkeleton animation="wave" width="55%" />
                        <BSkeleton animation="wave" width="70%" />
                    </div>
                </div>
            </div>
        </div>

        <div class="chatgxy-footer">
            <ChatInput v-model="query" :busy="busy" @submit="submitQuery" />
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.chatgxy-container {
    height: calc(100vh - #{$masthead-height} - 2rem);
    display: flex;
    flex-direction: column;
    background: $white;
    border-radius: $border-radius-large;
    overflow: hidden;
}

.chatgxy-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    background: $panel-bg-color;
    border-bottom: $border-default;

    .header-actions {
        display: flex;
        gap: 0.5rem;
    }
}

.chatgxy-body {
    flex: 1;
    display: flex;
    overflow: hidden;
}

.chatgxy-footer {
    padding: 0.75rem 1rem;
    background: $panel-bg-color;
    border-top: $border-default;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem 1.5rem;
    background: $white;
}

// Loading skeleton cell (stays in parent since it's not a real message)
.notebook-cell {
    margin-bottom: 1rem;
    animation: fadeIn 0.2s ease-out;

    &.response-cell {
        .cell-label {
            color: $text-muted;
        }

        .cell-content {
            border-left: 3px solid $brand-secondary;
            background: $panel-bg-color;
            padding: 0.75rem 1rem;
        }

        &.loading-cell {
            .cell-content {
                opacity: 0.7;
            }
        }
    }
}

.cell-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.025em;
    margin-bottom: 0.375rem;
    padding-left: 0.25rem;
}

.cell-content {
    border-radius: $border-radius-base;
    word-wrap: break-word;
    line-height: 1.6;
}

// History sidebar
.history-sidebar {
    width: 280px;
    border-right: $border-default;
    background: $panel-bg-color;
    display: flex;
    flex-direction: column;

    .history-header {
        padding: 0.75rem 1rem;
        border-bottom: $border-default;
        display: flex;
        justify-content: space-between;
        align-items: center;

        h5 {
            margin: 0;
            font-size: 0.875rem;
            font-weight: 600;
            color: $text-color;
        }
    }

    .history-list {
        flex: 1;
        overflow-y: auto;
    }

    .history-item {
        padding: 0.625rem 1rem;
        border-bottom: 1px solid darken($panel-bg-color, 5%);
        cursor: pointer;
        transition: background-color 0.15s;

        &:hover {
            background: darken($panel-bg-color, 3%);
        }

        .history-query {
            font-size: 0.8rem;
            color: $text-color;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin-bottom: 0.25rem;
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
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(4px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
