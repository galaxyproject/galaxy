<script setup lang="ts">
import {
    faAngleDoubleDown,
    faColumns,
    faExpand,
    faExternalLinkAlt,
    faFile,
    faMagic,
    faPlus,
    faSitemap,
    faTimes,
    faTrash,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BSkeleton } from "bootstrap-vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { getGalaxyInstance } from "@/app";
import { type AgentResponse, useAgentActions } from "@/composables/agentActions";
import { useMarkdown } from "@/composables/markdown";
import { useActiveContext } from "@/composables/useActiveContext";
import { useChatStore } from "@/stores/chatStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { getAgentIcon } from "./ChatGXY/agentTypes";
import type { ChatHistoryItem, ChatMessage } from "./ChatGXY/chatTypes";
import { generateId, scrollToBottom } from "./ChatGXY/chatUtils";

import ChatInput from "./ChatGXY/ChatInput.vue";
import ChatMessageCell from "./ChatGXY/ChatMessageCell.vue";
import Heading from "@/components/Common/Heading.vue";

const props = withDefaults(
    defineProps<{
        exchangeId?: string;
        compact?: boolean;
        docked?: boolean;
        panel?: boolean;
    }>(),
    {
        exchangeId: undefined,
        compact: false,
        docked: false,
        panel: false,
    },
);

const emit = defineEmits<{
    (e: "close"): void;
    (e: "undock"): void;
}>();

const router = useRouter();
const chatStore = useChatStore();

const { activeContext, contextLabel } = useActiveContext();
const contextDismissed = ref(false);

watch(activeContext, () => {
    contextDismissed.value = false;
});

const effectiveContext = computed(() => {
    if (contextDismissed.value || (!props.docked && !props.panel)) {
        return null;
    }
    return activeContext.value;
});

const contextIcon = computed(() => {
    switch (effectiveContext.value?.contextType) {
        case "tool":
            return faWrench;
        case "dataset":
            return faFile;
        case "workflow_editor":
        case "workflow_run":
            return faSitemap;
        default:
            return faMagic;
    }
});

const query = ref("");
const messages = ref<ChatMessage[]>([]);
const busy = ref(false);
const chatContainer = ref<HTMLElement>();
const selectedAgentType = ref("auto");
const currentChatId = ref<string | null>(null);
const hasLoadedInitialChat = ref(false);

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, removeNewlinesAfterList: true });
const { processingAction, handleAction } = useAgentActions();

onMounted(async () => {
    if (props.exchangeId) {
        await loadChatById(props.exchangeId);
    } else {
        await loadLatestChat();
    }

    if (!hasLoadedInitialChat.value) {
        showWelcome();
    }
});

watch(
    () => props.exchangeId,
    async (newId, oldId) => {
        if (newId === oldId) {
            return;
        }
        if (newId) {
            await loadChatById(newId);
        } else {
            startNewChat();
        }
    },
);

function showWelcome() {
    messages.value.push({
        id: generateId(),
        role: "assistant",
        content:
            "Welcome to ChatGXY. Ask about tools, workflows, errors, or data quality " +
            "and your question will be routed to the appropriate specialist agent.",
        timestamp: new Date(),
        agentType: "router",
        confidence: "high",
        feedback: null,
        isSystemMessage: true,
    });
}

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

    try {
        const { data, error } = await GalaxyApi().POST("/api/chat", {
            params: {
                query: {
                    agent_type: selectedAgentType.value,
                },
            },
            body: {
                query: currentQuery,
                context: effectiveContext.value ? JSON.stringify(effectiveContext.value) : null,
                exchange_id: currentChatId.value,
            },
        });

        if (error) {
            const errorText = errorMessageAsString(error, "Failed to get response from ChatGXY.");
            const errorMsg: ChatMessage = {
                id: generateId(),
                role: "assistant",
                content: `Error: ${errorText}`,
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
        console.error("Unexpected chat error:", e);
        const errorMsg: ChatMessage = {
            id: generateId(),
            role: "assistant",
            content: "Unexpected error occurred. Please try again.",
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

async function fetchConversation(exchangeId: string): Promise<boolean> {
    const { data: fullConversation } = await GalaxyApi().GET(`/api/chat/exchange/{exchange_id}/messages`, {
        params: {
            path: { exchange_id: exchangeId },
        },
    });

    if (!fullConversation || fullConversation.length === 0) {
        return false;
    }

    messages.value = fullConversation.map((msg: any, index: number) => {
        const message: ChatMessage = {
            id: `hist-${msg.role}-${exchangeId}-${index}`,
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

        return message;
    });

    currentChatId.value = exchangeId;
    nextTick(() => scrollToBottom(chatContainer.value));
    return true;
}

async function loadChatById(exchangeId: string) {
    try {
        const loaded = await fetchConversation(exchangeId);
        if (loaded) {
            hasLoadedInitialChat.value = true;
        }
    } catch (e) {
        console.error("Failed to load chat by ID:", e);
    }
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
            try {
                const loaded = await fetchConversation(latestChat.id);
                if (loaded) {
                    hasLoadedInitialChat.value = true;
                }
            } catch (e) {
                console.error("Error loading latest conversation:", e);
            }
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
            content: "New conversation started. How can I help?",
            timestamp: new Date(),
            agentType: "router",
            confidence: "high",
            feedback: null,
            isSystemMessage: true,
        },
    ];
    currentChatId.value = null;
    query.value = "";
}

async function deleteCurrentChat() {
    if (!currentChatId.value) {
        return;
    }
    try {
        const { error } = await GalaxyApi().DELETE("/api/chat/exchange/{exchange_id}", {
            params: { path: { exchange_id: currentChatId.value } },
        });
        if (!error) {
            startNewChat();
        }
    } catch (e) {
        console.error("Failed to delete chat:", e);
    }
}

function popOutToScratchbook() {
    const Galaxy = getGalaxyInstance();
    const path = currentChatId.value ? `/chatgxy/${currentChatId.value}` : "/chatgxy";
    const url = `${path}?compact=true`;
    Galaxy.frame.add({ title: "ChatGXY", url });
}

function dockToSide() {
    chatStore.setActiveChatId(currentChatId.value);
    chatStore.setLocation("right");
    chatStore.showChat();
    router.push("/");
}

function dockToBottomPanel() {
    chatStore.setActiveChatId(currentChatId.value);
    chatStore.setLocation("bottom");
    chatStore.showChat();
    router.push("/");
}

watch(currentChatId, (newId) => {
    if ((props.docked || props.panel) && newId) {
        chatStore.setActiveChatId(newId);
    }
});
</script>

<template>
    <div
        class="chatgxy-container"
        :class="{ 'chatgxy-compact': compact, 'chatgxy-docked': docked, 'chatgxy-panel': panel }">
        <!-- Docked side panel header -->
        <div v-if="docked" class="chatgxy-header chatgxy-header-docked">
            <span class="docked-title">
                <FontAwesomeIcon :icon="faMagic" fixed-width />
                ChatGXY
            </span>
            <div class="header-actions">
                <button class="btn btn-sm btn-outline-primary" title="Start New Chat" @click="startNewChat">
                    <FontAwesomeIcon :icon="faPlus" fixed-width />
                </button>
                <button class="btn btn-sm btn-outline-primary" title="Open in center view" @click="emit('undock')">
                    <FontAwesomeIcon :icon="faExpand" fixed-width />
                </button>
                <button class="btn btn-sm btn-outline-secondary" title="Close panel" @click="emit('close')">
                    <FontAwesomeIcon :icon="faTimes" fixed-width />
                </button>
            </div>
        </div>
        <!-- Center view header -->
        <div v-else-if="!compact && !panel" class="chatgxy-header">
            <Heading h2 :icon="faMagic" size="lg">
                <span>ChatGXY</span>
            </Heading>
            <div class="header-actions">
                <button class="btn btn-sm btn-outline-primary" title="Start New Chat" @click="startNewChat">
                    <FontAwesomeIcon :icon="faPlus" fixed-width />
                    New
                </button>
                <button
                    v-if="currentChatId"
                    class="btn btn-sm btn-outline-danger"
                    title="Delete this conversation"
                    @click="deleteCurrentChat">
                    <FontAwesomeIcon :icon="faTrash" fixed-width />
                </button>
                <button class="btn btn-sm btn-outline-primary" title="Dock to side panel" @click="dockToSide">
                    <FontAwesomeIcon :icon="faColumns" fixed-width />
                </button>
                <button class="btn btn-sm btn-outline-primary" title="Dock to bottom panel" @click="dockToBottomPanel">
                    <FontAwesomeIcon :icon="faAngleDoubleDown" fixed-width />
                </button>
                <button
                    class="btn btn-sm btn-outline-primary"
                    title="Open in floating window"
                    @click="popOutToScratchbook">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                </button>
            </div>
        </div>

        <div v-if="(docked || panel) && effectiveContext" class="context-indicator">
            <span class="context-badge">
                <FontAwesomeIcon :icon="contextIcon" fixed-width />
                {{ contextLabel }}
            </span>
            <button class="context-dismiss" title="Dismiss context" @click="contextDismissed = true">
                <FontAwesomeIcon :icon="faTimes" />
            </button>
        </div>

        <div ref="chatContainer" class="chat-messages">
            <ChatMessageCell
                v-for="message in messages"
                :key="message.id"
                :message="message"
                :render-markdown="renderMarkdown"
                :processing-action="processingAction"
                @feedback="sendFeedback"
                @handle-action="handleAction" />

            <!-- Loading state -->
            <div v-if="busy" class="loading-entry">
                <div class="loading-gutter">
                    <span class="loading-indicator">
                        <FontAwesomeIcon :icon="getAgentIcon(selectedAgentType)" fixed-width />
                    </span>
                </div>
                <div class="loading-body">
                    <BSkeleton animation="wave" width="85%" />
                    <BSkeleton animation="wave" width="55%" />
                    <BSkeleton animation="wave" width="70%" />
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
    border-radius: 0.5rem;
    overflow: hidden;
}

.chatgxy-compact {
    height: 100vh;

    .chat-messages {
        padding: 0.75rem 1rem;
    }

    .chatgxy-footer {
        padding: 0.5rem 0.75rem;
    }
}

.chatgxy-docked,
.chatgxy-panel {
    height: 100%;
    border-radius: 0;
}

.chatgxy-header-docked {
    padding: 0.5rem 0.75rem;

    .docked-title {
        font-weight: 600;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }
}

.context-indicator {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.25rem 0.75rem;
    background: rgba($brand-primary, 0.06);
    border-bottom: 1px solid rgba($brand-primary, 0.12);
    font-size: 0.8rem;
    color: $brand-primary;

    .context-badge {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        font-weight: 500;
    }

    .context-dismiss {
        background: none;
        border: none;
        color: inherit;
        opacity: 0.6;
        cursor: pointer;
        padding: 0.125rem;

        &:hover {
            opacity: 1;
        }
    }
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

.chatgxy-footer {
    padding: 0.75rem 1rem;
    background: $panel-bg-color;
    border-top: $border-default;
    box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.05);
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem 1.5rem;
    background: $white;
}

// Loading skeleton
.loading-entry {
    display: flex;
    gap: 0;
    margin-top: 1.25rem;
    animation: fadeIn 0.2s ease-out;
}

.loading-gutter {
    flex-shrink: 0;
    width: 2rem;
    padding-top: 0.125rem;
}

.loading-indicator {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    background: rgba($brand-primary, 0.08);
    color: $brand-primary;
    font-size: 0.65rem;
}

.loading-body {
    flex: 1;
    opacity: 0.6;
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
