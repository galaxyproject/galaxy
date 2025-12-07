<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faClock,
    faHistory,
    faMagic,
    faPaperPlane,
    faThumbsDown,
    faThumbsUp,
    faTrash,
    faUser,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BSkeleton } from "bootstrap-vue";
import { nextTick, onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import { type ActionSuggestion, type AgentResponse, useAgentActions } from "@/composables/agentActions";
import { useMarkdown } from "@/composables/markdown";
import { errorMessageAsString } from "@/utils/simple-error";

import ActionCard from "./ChatGXY/ActionCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faThumbsUp, faThumbsDown, faPaperPlane, faUser, faMagic, faHistory, faTrash, faClock);

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

const agentTypes = [
    { value: "auto", label: "🧙 Auto (Router)", description: "Let the wizard decide" },
    { value: "error_analysis", label: "🔍 Error Analysis", description: "Debug tool errors" },
    { value: "tool_recommendation", label: "🔧 Tool Recommendation", description: "Find the right tools" },
    { value: "dspy_tool_recommendation", label: "🤖 DSPy Tools", description: "Advanced reasoning for tool selection" },
    { value: "custom_tool", label: "⚡ Custom Tool", description: "Create custom tools" },
    { value: "dataset_analyzer", label: "📊 Dataset Analyzer", description: "Analyze datasets" },
    { value: "gtn_training", label: "📚 Training Materials", description: "Find tutorials and guides" },
];

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
            behavior: 'auto' // Use 'smooth' if you want animated scrolling
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

function getAgentIcon(agentType?: string) {
    switch (agentType) {
        case "router":
            return "🧙";
        case "error_analysis":
            return "🔍";
        case "tool_recommendation":
            return "🔧";
        case "dspy_tool_recommendation":
            return "🤖";
        case "custom_tool":
            return "⚡";
        case "dataset_analyzer":
            return "📊";
        case "gtn_training":
            return "📚";
        default:
            return "🤖";
    }
}

function getAgentLabel(agentType?: string) {
    const agent = agentTypes.find((a) => a.value === agentType);
    return agent?.label.split(" ").slice(1).join(" ") || "AI Assistant";
}

function getAgentDescription(agentType?: string) {
    const descriptions = {
        "router": "Intelligent query routing and task classification",
        "error_analysis": "Debugging tool errors and job failures",
        "tool_recommendation": "Finding the right Galaxy tools for your analysis",
        "dspy_tool_recommendation": "Advanced reasoning for tool selection using DSPy",
        "custom_tool": "Creating custom Galaxy tools and wrappers", 
        "dataset_analyzer": "Analyzing datasets and data quality assessment",
        "gtn_training": "Finding tutorials and training materials"
    };
    return descriptions[agentType as keyof typeof descriptions] || "General AI assistance";
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
            chatHistory.value = data as ChatHistoryItem[];
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
            const latestChat = data[0] as ChatHistoryItem;
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

// Format timestamp for display
function formatTime(timestamp: string) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));

    if (hours < 1) {
        const minutes = Math.floor(diff / (1000 * 60));
        return `${minutes}m ago`;
    } else if (hours < 24) {
        return `${hours}h ago`;
    } else {
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    }
}
</script>

<template>
    <div class="chatgxy-container card">
        <div class="card-header">
            <div class="d-flex align-items-center justify-content-between">
                <h3 class="mb-0 d-flex align-items-center">
                    <FontAwesomeIcon :icon="faMagic" fixed-width />
                    ChatGXY
                    <span v-if="currentChatId" class="badge badge-info ml-2" style="font-size: 0.6em">
                        Continuing Chat #{{ currentChatId }}
                    </span>
                </h3>
                <div class="d-flex align-items-center">
                    <button class="btn btn-sm btn-primary mr-2" title="Start New Chat" @click="startNewChat">
                        <FontAwesomeIcon :icon="faPaperPlane" fixed-width />
                        New Chat
                    </button>
                    <button
                        class="btn btn-sm btn-outline-secondary mr-3"
                        :title="showHistory ? 'Hide History' : 'Show History'"
                        @click="toggleHistory">
                        <FontAwesomeIcon :icon="faHistory" fixed-width />
                        History
                    </button>
                    <div class="agent-selector">
                        <label for="agent-select" class="mr-2">Agent:</label>
                        <select id="agent-select" v-model="selectedAgentType" class="form-control form-control-sm">
                            <option v-for="agent in agentTypes" :key="agent.value" :value="agent.value">
                                {{ agent.label }}
                            </option>
                        </select>
                    </div>
                </div>
            </div>
        </div>

        <div class="card-body d-flex">
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
                            <span class="history-agent">{{ getAgentIcon(item.agent_type) }}</span>
                            <span class="history-time">
                                <FontAwesomeIcon :icon="faClock" class="mr-1" />
                                {{ formatTime(item.timestamp) }}
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
                    :class="['message', message.role === 'user' ? 'user-message' : 'assistant-message']">
                    <div class="message-header">
                        <span class="message-icon">
                            <FontAwesomeIcon v-if="message.role === 'user'" :icon="faUser" fixed-width />
                            <span v-else>{{ getAgentIcon(message.agentType) }}</span>
                        </span>
                        <div class="message-agent-info">
                            <span class="message-role">
                                {{ message.role === "user" ? "You" : getAgentLabel(message.agentType) }}
                            </span>
                            <span 
                                v-if="message.role === 'assistant' && message.agentType"
                                class="agent-description"
                                :title="getAgentDescription(message.agentType)">
                                {{ getAgentDescription(message.agentType) }}
                            </span>
                        </div>
                        <div class="message-badges">
                            <span
                                v-if="message.confidence"
                                class="confidence-badge"
                                :class="`confidence-${message.confidence}`"
                                :title="`Confidence: ${message.confidence}`">
                                {{ message.confidence }}
                            </span>
                            <span v-if="message.routingInfo" class="routing-info" :title="message.routingInfo.reasoning">
                                → {{ getAgentLabel(message.routingInfo.selected_agent) }}
                            </span>
                        </div>
                    </div>

                    <div class="message-content">
                        <!-- eslint-disable-next-line vue/no-v-html -->
                        <div v-if="message.role === 'assistant'" v-html="renderMarkdown(message.content)" />
                        <div v-else>{{ message.content }}</div>
                    </div>

                    <!-- Action suggestions for assistant messages -->
                    <ActionCard
                        v-if="message.role === 'assistant' && message.suggestions?.length"
                        :suggestions="message.suggestions"
                        :processing-action="processingAction"
                        @handle-action="(action) => handleAction(action, message.agentResponse || {})" />

                    <div
                        v-if="
                            message.role === 'assistant' &&
                            !message.content.startsWith('❌') &&
                            !message.isSystemMessage
                        "
                        class="message-feedback">
                        <button
                            class="btn btn-link btn-sm"
                            :disabled="message.feedback !== null"
                            :class="{ 'feedback-given': message.feedback === 'up' }"
                            @click="sendFeedback(message.id, 'up')">
                            <FontAwesomeIcon :icon="faThumbsUp" fixed-width />
                        </button>
                        <button
                            class="btn btn-link btn-sm"
                            :disabled="message.feedback !== null"
                            :class="{ 'feedback-given': message.feedback === 'down' }"
                            @click="sendFeedback(message.id, 'down')">
                            <FontAwesomeIcon :icon="faThumbsDown" fixed-width />
                        </button>
                        <span v-if="message.feedback" class="feedback-text">Thanks for feedback!</span>
                    </div>
                </div>

                <div v-if="busy" class="message assistant-message">
                    <div class="message-header">
                        <span class="message-icon">{{ getAgentIcon(selectedAgentType) }}</span>
                        <span class="message-role">{{ getAgentLabel(selectedAgentType) }}</span>
                    </div>
                    <div class="message-content">
                        <BSkeleton animation="wave" width="85%" />
                        <BSkeleton animation="wave" width="55%" />
                        <BSkeleton animation="wave" width="70%" />
                    </div>
                </div>
            </div>
        </div>

        <div class="card-footer">
            <div class="chat-input-container">
                <label for="chat-input" class="sr-only">Chat message</label>
                <textarea
                    id="chat-input"
                    v-model="query"
                    :disabled="busy"
                    placeholder="Ask me anything about Galaxy..."
                    rows="2"
                    class="form-control chat-input"
                    @keydown.enter.prevent="!$event.shiftKey && submitQuery()" />
                <button :disabled="busy || !query.trim()" class="btn btn-primary send-button" @click="submitQuery">
                    <FontAwesomeIcon v-if="!busy" :icon="faPaperPlane" fixed-width />
                    <LoadingSpan v-else message="" />
                </button>
            </div>
            <div class="chat-hints">
                <small class="text-muted">
                    Press Enter to send, Shift+Enter for new line. Try asking about tools, errors, or workflows!
                </small>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.chatgxy-container {
    height: 80vh;
    display: flex;
    flex-direction: column;

    .card-body {
        flex: 1;
        overflow: hidden;
        padding: 0;
    }

    .card-footer {
        flex-shrink: 0;
        position: sticky;
        bottom: 0;
        background: white;
        border-top: 1px solid #dee2e6;
        z-index: 10;
    }
}

.agent-selector {
    display: flex;
    align-items: center;

    select {
        width: 200px;
    }
}

.chat-messages {
    height: 100%;
    overflow-y: auto;
    padding: 1rem;
    background: #f8f9fa;
}

.message {
    margin-bottom: 1.5rem;
    animation: fadeIn 0.3s;

    &.user-message {
        .message-content {
            background: #007bff;
            color: white;
            margin-left: 2rem;
            margin-right: 0;
            border-radius: 18px 18px 4px 18px;
        }
    }

    &.assistant-message {
        .message-content {
            background: white;
            color: #333;
            margin-left: 0;
            margin-right: 2rem;
            border-radius: 18px 18px 18px 4px;
            border: 1px solid #dee2e6;
        }
    }
}

.message-header {
    display: flex;
    align-items: center;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: #6c757d;

    .message-icon {
        margin-right: 0.5rem;
    }

    .message-role {
        font-weight: 600;
        margin-right: 0.5rem;
    }
}

.message-agent-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;

    .agent-icon {
        font-size: 1.1rem;
    }

    .agent-name {
        font-weight: 600;
        color: #495057;
    }
}

.agent-description {
    font-size: 0.75rem;
    color: #6c757d;
    font-style: italic;
    margin-left: 1.6rem;
    margin-bottom: 0.25rem;
}

.message-badges {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-left: 1.6rem;
}

.confidence-badge {
    padding: 0.125rem 0.5rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;

    &.confidence-high {
        background: #d4edda;
        color: #155724;
    }

    &.confidence-medium {
        background: #fff3cd;
        color: #856404;
    }

    &.confidence-low {
        background: #f8d7da;
        color: #721c24;
    }
}

.routing-info {
    margin-left: 0.5rem;
    padding: 0.125rem 0.5rem;
    background: #e7f3ff;
    color: #0056b3;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 500;
    cursor: help;

    &:hover {
        background: #d1e7fd;
    }
}

.message-content {
    padding: 0.75rem 1rem;
    word-wrap: break-word;

    ::v-deep {
        p:last-child {
            margin-bottom: 0;
        }

        code {
            background: rgba(0, 0, 0, 0.05);
            padding: 0.125rem 0.25rem;
            border-radius: 3px;
        }

        pre {
            background: #f6f8fa;
            padding: 0.75rem;
            border-radius: 6px;
            overflow-x: auto;
        }
    }
}

.message-feedback {
    margin-top: 0.5rem;
    margin-left: 2rem;

    .feedback-given {
        color: #28a745;
    }

    .feedback-text {
        font-size: 0.75rem;
        color: #6c757d;
        margin-left: 0.5rem;
    }
}

.chat-input-container {
    display: flex;
    gap: 0.5rem;
    align-items: flex-end;
    min-height: 44px; /* Ensure consistent height */

    .chat-input {
        flex: 1;
        resize: none; /* Prevent manual resizing */
        transition: none; /* Prevent transition effects */
    }

    .send-button {
        flex-shrink: 0;
        align-self: flex-end;
    }
}

.chat-hints {
    margin-top: 0.5rem;
    text-align: center;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

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

// History Sidebar Styles
.history-sidebar {
    width: 300px;
    border-right: 1px solid #dee2e6;
    background: white;
    display: flex;
    flex-direction: column;

    .history-header {
        padding: 1rem;
        border-bottom: 1px solid #dee2e6;
        display: flex;
        justify-content: space-between;
        align-items: center;

        h5 {
            margin: 0;
            font-size: 1rem;
        }
    }

    .history-list {
        flex: 1;
        overflow-y: auto;
    }

    .history-item {
        padding: 0.75rem 1rem;
        border-bottom: 1px solid #f0f0f0;
        cursor: pointer;
        transition: background-color 0.2s;

        &:hover {
            background-color: #f8f9fa;
        }

        .history-query {
            font-size: 0.875rem;
            color: #333;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin-bottom: 0.25rem;
        }

        .history-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            color: #6c757d;

            .history-time {
                display: flex;
                align-items: center;
            }
        }
    }
}

</style>
