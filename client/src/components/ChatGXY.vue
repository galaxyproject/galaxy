<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
    faBug,
    faChartBar,
    faClock,
    faGraduationCap,
    faHistory,
    faMagic,
    faPaperPlane,
    faPlus,
    faRobot,
    faRoute,
    faThumbsDown,
    faThumbsUp,
    faTrash,
    faUser,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BSkeleton } from "bootstrap-vue";
import { nextTick, onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import { type ActionSuggestion, type AgentResponse, useAgentActions } from "@/composables/agentActions";
import { useMarkdown } from "@/composables/markdown";
import { errorMessageAsString } from "@/utils/simple-error";

import ActionCard from "./ChatGXY/ActionCard.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    agentType?: string;
    confidence?: string;
    feedback?: "up" | "down" | null;
    agentResponse?: AgentResponse;
    suggestions?: ActionSuggestion[];
    isSystemMessage?: boolean; // Flag for welcome/placeholder messages that shouldn't have feedback
    routingInfo?: {
        selected_agent: string;
        reasoning: string;
    };
}

interface ChatHistoryItem {
    id: number;
    query: string;
    response: string;
    agent_type: string;
    agent_response?: AgentResponse; // Full agent response with suggestions
    timestamp: string;
    feedback?: number | null;
}

const query = ref("");
const messages = ref<Message[]>([]);
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

interface AgentType {
    value: string;
    label: string;
    icon: IconDefinition;
    description: string;
}

const agentTypes: AgentType[] = [
    { value: "auto", label: "Auto (Router)", icon: faMagic, description: "Intelligent routing" },
    { value: "error_analysis", label: "Error Analysis", icon: faBug, description: "Debug tool errors" },
    { value: "tool_recommendation", label: "Tool Recommendation", icon: faWrench, description: "Find the right tools" },
    { value: "dspy_tool_recommendation", label: "DSPy Tools", icon: faRobot, description: "Advanced tool selection" },
    { value: "custom_tool", label: "Custom Tool", icon: faPlus, description: "Create custom tools" },
    { value: "dataset_analyzer", label: "Dataset Analyzer", icon: faChartBar, description: "Analyze datasets" },
    { value: "gtn_training", label: "Training Materials", icon: faGraduationCap, description: "Find tutorials" },
];

// Map agent types to their icons for quick lookup
const agentIconMap: Record<string, IconDefinition> = {
    auto: faMagic,
    router: faRoute,
    error_analysis: faBug,
    tool_recommendation: faWrench,
    dspy_tool_recommendation: faRobot,
    custom_tool: faPlus,
    dataset_analyzer: faChartBar,
    gtn_training: faGraduationCap,
};

onMounted(async () => {
    // Try to load the most recent chat
    await loadLatestChat();

    // If no chat was loaded, show the welcome message
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

function generateId() {
    return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

async function submitQuery() {
    if (!query.value.trim()) {
        return;
    }

    const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: query.value,
        timestamp: new Date(),
        feedback: null,
    };

    messages.value.push(userMessage);
    const currentQuery = query.value;
    query.value = "";

    // Scroll to bottom after adding user message
    await nextTick();
    scrollToBottom();

    busy.value = true;
    errorMessage.value = "";

    try {
        const { data, error } = await GalaxyApi().POST("/api/chat", {
            body: {
                job_id: null,
                query: currentQuery,
                agent_type: selectedAgentType.value,
                exchange_id: currentChatId.value, // Backend will load full conversation history
            } as any,
        });

        if (error) {
            errorMessage.value = errorMessageAsString(error, "Failed to get response from ChatGXY.");
            const errorMsg: Message = {
                id: generateId(),
                role: "assistant",
                content: `❌ Error: ${errorMessage.value}`,
                timestamp: new Date(),
                agentType: selectedAgentType.value,
                confidence: "low",
                feedback: null,
            };
            messages.value.push(errorMsg);

            // Scroll to bottom after adding error message
            await nextTick();
            scrollToBottom();
        } else if (data) {
            // Extract agent response if available
            const agentResponse = (data as any)?.agent_response;
            const content = typeof data === "string" ? data : (data as any)?.response || "No response received";

            // Get the exchange ID if returned
            const exchangeId = (data as any)?.exchange_id;
            if (exchangeId) {
                currentChatId.value = exchangeId;
            }

            const assistantMessage: Message = {
                id: generateId(),
                role: "assistant",
                content: content,
                timestamp: new Date(),
                agentType:
                    agentResponse?.agent_type ||
                    (selectedAgentType.value === "auto" ? "router" : selectedAgentType.value),
                confidence: agentResponse?.confidence || (data as any)?.confidence || "medium",
                feedback: null,
                agentResponse: agentResponse,
                suggestions: agentResponse?.suggestions || [],
                routingInfo: (data as any)?.routing_info,
            };
            messages.value.push(assistantMessage);

            // Scroll to bottom after adding assistant message
            await nextTick();
            scrollToBottom();
        }
    } catch (e) {
        errorMessage.value = `Unexpected error: ${e}`;
        const errorMsg: Message = {
            id: generateId(),
            role: "assistant",
            content: `❌ Unexpected error occurred. Please try again.`,
            timestamp: new Date(),
            agentType: selectedAgentType.value,
            confidence: "low",
            feedback: null,
        };
        messages.value.push(errorMsg);

        // Scroll to bottom after adding error message
        await nextTick();
        scrollToBottom();
    } finally {
        busy.value = false;
        await nextTick();
        scrollToBottom();
    }
}

function scrollToBottom() {
    if (chatContainer.value) {
        // Use smooth scrolling and avoid focus disruption
        chatContainer.value.scrollTo({
            top: chatContainer.value.scrollHeight,
            behavior: "auto", // Use 'smooth' if you want animated scrolling
        });
    }
}

async function sendFeedback(messageId: string, value: "up" | "down") {
    const message = messages.value.find((m) => m.id === messageId);
    if (message) {
        // Update UI immediately
        message.feedback = value;

        // Only persist if we have a currentChatId (for saved chats)
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
                    // Revert on error
                    message.feedback = null;
                }
            } catch (e) {
                console.error("Failed to save feedback:", e);
                // Revert on error
                message.feedback = null;
            }
        }
    }
}

function getAgentIcon(agentType?: string): IconDefinition {
    return agentIconMap[agentType || ""] || faRobot;
}

function getAgentLabel(agentType?: string) {
    const agent = agentTypes.find((a) => a.value === agentType);
    return agent?.label || "AI Assistant";
}

function getAgentResponseOrEmpty(response?: AgentResponse): AgentResponse {
    return (
        response || ({ content: "", agent_type: "", confidence: "low", suggestions: [], metadata: {} } as AgentResponse)
    );
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
            // Also clear current chat if it was from history
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
    // Try to load the full conversation from the backend
    try {
        const { data: fullConversation } = await GalaxyApi().GET(`/api/chat/exchange/{exchange_id}/messages`, {
            params: {
                path: {
                    exchange_id: item.id,
                },
            },
        });

        if (fullConversation && fullConversation.length > 0) {
            // Clear and rebuild messages from full conversation
            messages.value = [];

            fullConversation.forEach((msg: any, index: number) => {
                const message: Message = {
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
            // Fallback to single message if no full conversation available
            loadSingleMessageFallback(item);
        }

        currentChatId.value = item.id;
        showHistory.value = false;
        nextTick(() => scrollToBottom());
    } catch (error) {
        console.error("Error loading full conversation:", error);
        // Fallback to simple loading on error
        loadSingleMessageFallback(item);
    }
}

function loadSingleMessageFallback(item: ChatHistoryItem) {
    // Fallback method for loading just the first message pair
    const userMessage: Message = {
        id: `hist-user-${item.id}`,
        role: "user",
        content: item.query,
        timestamp: new Date(item.timestamp),
        feedback: null,
    };

    const assistantMessage: Message = {
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
    nextTick(() => scrollToBottom());
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
    // Clear messages and reset to welcome message
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
                <div
                    v-for="message in messages"
                    :key="message.id"
                    :class="['notebook-cell', message.role === 'user' ? 'query-cell' : 'response-cell']">
                    <!-- Query cell (user input) -->
                    <template v-if="message.role === 'user'">
                        <div class="cell-label">
                            <FontAwesomeIcon :icon="faUser" fixed-width />
                            <span>Query</span>
                        </div>
                        <div class="cell-content">{{ message.content }}</div>
                    </template>

                    <!-- Response cell (assistant output) -->
                    <template v-else>
                        <div class="cell-label">
                            <FontAwesomeIcon :icon="getAgentIcon(message.agentType)" fixed-width />
                            <span>{{ getAgentLabel(message.agentType) }}</span>
                            <span
                                v-if="message.routingInfo"
                                class="routing-badge"
                                :title="message.routingInfo.reasoning">
                                via Router
                            </span>
                        </div>
                        <div class="cell-content">
                            <!-- eslint-disable-next-line vue/no-v-html -->
                            <div v-html="renderMarkdown(message.content)" />

                            <!-- Action suggestions -->
                            <ActionCard
                                v-if="message.suggestions?.length"
                                :suggestions="message.suggestions"
                                :processing-action="processingAction"
                                @handle-action="
                                    (action) => handleAction(action, getAgentResponseOrEmpty(message.agentResponse))
                                " />
                        </div>
                        <div v-if="!message.content.startsWith('❌') && !message.isSystemMessage" class="cell-footer">
                            <button
                                class="feedback-btn"
                                :disabled="message.feedback !== null"
                                :class="{ active: message.feedback === 'up' }"
                                title="Helpful"
                                @click="sendFeedback(message.id, 'up')">
                                <FontAwesomeIcon :icon="faThumbsUp" fixed-width />
                            </button>
                            <button
                                class="feedback-btn"
                                :disabled="message.feedback !== null"
                                :class="{ active: message.feedback === 'down' }"
                                title="Not helpful"
                                @click="sendFeedback(message.id, 'down')">
                                <FontAwesomeIcon :icon="faThumbsDown" fixed-width />
                            </button>
                            <span v-if="message.feedback" class="feedback-text">Thanks!</span>
                        </div>
                    </template>
                </div>

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
            <div class="chat-input-container">
                <label for="chat-input" class="sr-only">Chat message</label>
                <textarea
                    id="chat-input"
                    v-model="query"
                    :disabled="busy"
                    placeholder="Ask about tools, workflows, errors, or anything Galaxy..."
                    rows="1"
                    class="form-control chat-input"
                    @keydown.enter.prevent="!$event.shiftKey && submitQuery()" />
                <button :disabled="busy || !query.trim()" class="btn btn-primary send-button" @click="submitQuery">
                    <FontAwesomeIcon v-if="!busy" :icon="faPaperPlane" fixed-width />
                    <LoadingSpan v-else message="" />
                </button>
            </div>
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

// Notebook-style cells
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem 1.5rem;
    background: $white;
}

.notebook-cell {
    margin-bottom: 1rem;
    animation: fadeIn 0.2s ease-out;

    &.query-cell {
        .cell-label {
            color: $brand-primary;
        }

        .cell-content {
            border-left: 3px solid $brand-primary;
            background: rgba($brand-primary, 0.04);
            padding: 0.75rem 1rem;
            font-size: 0.95rem;
            color: $text-color;
        }
    }

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

.routing-badge {
    font-weight: 400;
    font-size: 0.65rem;
    color: $text-light;
    text-transform: none;
    cursor: help;

    &::before {
        content: "·";
        margin: 0 0.25rem;
    }
}

.cell-content {
    border-radius: $border-radius-base;
    word-wrap: break-word;
    line-height: 1.6;

    :deep(p:last-child) {
        margin-bottom: 0;
    }

    :deep(p:first-child) {
        margin-top: 0;
    }

    :deep(code) {
        background: rgba($brand-dark, 0.08);
        padding: 0.125rem 0.375rem;
        border-radius: $border-radius-base;
        font-family: $font-family-monospace;
        font-size: 0.85em;
    }

    :deep(pre) {
        background: $white;
        border: $border-default;
        padding: 0.75rem;
        border-radius: $border-radius-base;
        overflow-x: auto;
        margin: 0.75rem 0;

        code {
            background: none;
            padding: 0;
        }
    }

    :deep(ul),
    :deep(ol) {
        margin-bottom: 0.75rem;
        padding-left: 1.5rem;
    }

    :deep(li) {
        margin-bottom: 0.25rem;
    }
}

.cell-footer {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    margin-top: 0.5rem;
    padding-left: 0.25rem;
}

.feedback-btn {
    background: none;
    border: none;
    padding: 0.25rem 0.5rem;
    color: $text-light;
    cursor: pointer;
    border-radius: $border-radius-base;
    transition: all 0.15s;

    &:hover:not(:disabled) {
        color: $brand-primary;
        background: rgba($brand-primary, 0.08);
    }

    &:disabled {
        cursor: default;
        opacity: 0.5;
    }

    &.active {
        color: $brand-success;
    }
}

.feedback-text {
    font-size: 0.7rem;
    color: $text-light;
    margin-left: 0.25rem;
}

// Input area
.chat-input-container {
    display: flex;
    gap: 0.5rem;
    align-items: flex-end;

    .chat-input {
        flex: 1;
        resize: none;
        border-radius: $border-radius-base;
        padding: 0.625rem 0.875rem;
        border: $border-default;
        font-size: 0.9rem;
        min-height: 2.5rem;
        max-height: 8rem;

        &:focus {
            border-color: $brand-primary;
            box-shadow: 0 0 0 2px rgba($brand-primary, 0.1);
            outline: none;
        }
    }

    .send-button {
        flex-shrink: 0;
        border-radius: $border-radius-base;
        padding: 0.5rem 0.875rem;
    }
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

// Animations
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

// Accessibility
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
</style>
