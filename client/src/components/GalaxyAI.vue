<script setup lang="ts">
import { faFile, faMagic, faSitemap, faTimes, faTrash, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BSkeleton } from "bootstrap-vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { type AgentResponse, useAgentActions } from "@/composables/agentActions";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useMarkdown } from "@/composables/markdown";
import { useToast } from "@/composables/toast";
import { useActiveContext } from "@/composables/useActiveContext";
import { buildEntityContext, parseMentions, resolveMentions } from "@/composables/useEntityMentions";
import { useChatStore } from "@/stores/chatStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { getAgentIcon } from "./GalaxyAI/agentTypes";
import type { ChatHistoryItem, ChatMessage } from "./GalaxyAI/chatTypes";
import { generateId, scrollToBottom } from "./GalaxyAI/chatUtils";

import ChatActions from "./GalaxyAI/ChatActions.vue";
import ChatInput from "./GalaxyAI/ChatInput.vue";
import ChatMessageCell from "./GalaxyAI/ChatMessageCell.vue";
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

const { confirm } = useConfirmDialog();
const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const Toast = useToast();

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

/** The chat is in "route mode": It's being viewed in the center and the route starts with `/galaxyai`
 * _(and we are not in the window manager)_. */
const isRouteMode = computed(() => chatStore.isCenterMode && !props.compact && route.path.startsWith("/galaxyai"));

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
    if (props.exchangeId && props.exchangeId !== "new") {
        await fetchConversation(props.exchangeId);
    } else if (props.docked || props.panel || props.exchangeId === "new") {
        startNewChat();
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
        if (newId && newId !== "new") {
            await fetchConversation(newId);
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
            "Welcome to GalaxyAI. Ask about tools, workflows, errors, or data quality " +
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
        const parsed = parseMentions(currentQuery);
        const resolved = resolveMentions(parsed);
        const entityContext = buildEntityContext(resolved);

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
                entity_context: entityContext,
            },
        });

        if (error) {
            const errorText = errorMessageAsString(error, "Failed to get response from GalaxyAI.");
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

async function selectClarificationOption(option: string) {
    // A quick-reply to a clarifying question -- send it as the next message. The router
    // includes the clarification turn when routing, so a terse option still routes.
    query.value = option;
    await submitQuery();
}

async function sendFeedback(messageId: string, value: "up" | "down") {
    const message = messages.value.find((m) => m.id === messageId);
    if (message) {
        message.feedback = value;

        if (currentChatId.value) {
            const feedbackValue = value === "up" ? 1 : 0;
            const { error } = await GalaxyApi().PUT("/api/chat/exchange/{exchange_id}/feedback", {
                params: {
                    path: { exchange_id: currentChatId.value },
                },
                body: feedbackValue,
            });

            if (error) {
                Toast.error(errorMessageAsString(error), "Failed to save feedback");
                message.feedback = null;
            }
        }
    }
}

async function fetchConversation(exchangeId: string) {
    if (exchangeId === "new") {
        startNewChat();
        return;
    }

    const { data: fullConversation, error } = await GalaxyApi().GET(`/api/chat/exchange/{exchange_id}/messages`, {
        params: {
            path: { exchange_id: exchangeId },
        },
    });

    if (error) {
        Toast.error(errorMessageAsString(error, "Failed to load conversation."), "Error loading conversation");
        return;
    }
    if (!fullConversation || fullConversation.length === 0) {
        return;
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

    hasLoadedInitialChat.value = true;
}

async function loadLatestChat() {
    const { data, error } = await GalaxyApi().GET("/api/chat/history", {
        params: {
            query: { limit: 1 },
        },
    });

    if (error) {
        Toast.error(errorMessageAsString(error), "Failed to load latest chat");
    } else if (data && data.length > 0) {
        const latestChat = data[0] as unknown as ChatHistoryItem;
        await fetchConversation(latestChat.id);
    }
}

function startNewChat() {
    hasLoadedInitialChat.value = true;
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
    if (props.docked || props.panel) {
        chatStore.setActiveChatId(null);
    }
}

async function deleteCurrentChat() {
    if (!currentChatId.value) {
        return;
    }

    const confirmed = await confirm("Are you sure you want to delete this conversation?", {
        title: "Delete Conversation",
        okText: "Delete",
        okIcon: faTrash,
        okColor: "red",
    });
    if (confirmed) {
        try {
            await chatStore.deleteChatById(currentChatId.value);
            startNewChat();
        } catch (e) {
            Toast.error(
                errorMessageAsString(e, "Error occured while trying to delete the conversation"),
                "Failed to delete conversation.",
            );
        }
    }
}

function dockTo(location: "right" | "bottom") {
    chatStore.dockChat(location, currentChatId.value);
    if (route.path.startsWith("/galaxyai")) {
        router.push("/");
    }
}

watch(currentChatId, async (newId) => {
    if (props.docked || props.panel) {
        chatStore.setActiveChatId(newId);
    }

    if (newId && !chatStore.chatHistory.some((item) => item.id === newId)) {
        try {
            await chatStore.loadHistory();
        } catch (e) {
            Toast.error(errorMessageAsString(e), "Failed to load chat history");
        }
    }

    // Ensure the route is updated to reflect the current chat in center (non-window manager) mode
    if (isRouteMode.value) {
        const targetPath = newId ? `/galaxyai/${newId}` : "/galaxyai/new";
        if (route.path !== targetPath) {
            router.replace(targetPath);
        }
    }
});
</script>

<template>
    <div
        class="galaxyai-container"
        :class="{ 'galaxyai-compact': compact, 'galaxyai-docked': docked, 'galaxyai-panel': panel }">
        <div
            v-if="docked || (!compact && !panel)"
            class="galaxyai-header"
            :class="{ 'galaxyai-header-docked': docked }">
            <Heading :icon="faMagic" :size="docked ? 'sm' : 'lg'">
                <span class="heading-label">GalaxyAI</span>
            </Heading>
            <ChatActions
                :source="docked ? 'docked' : 'center'"
                :enable-delete="Boolean(currentChatId)"
                @delete="deleteCurrentChat"
                @dock-to="dockTo" />
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
                @handle-action="handleAction"
                @select-clarification-option="selectClarificationOption" />

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

        <div class="galaxyai-footer">
            <ChatInput v-model="query" :busy="busy" @submit="submitQuery" />
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.galaxyai-container {
    height: calc(100vh - #{$masthead-height} - 2rem);
    display: flex;
    flex-direction: column;
    background: $white;
    border-radius: 0.5rem;
    overflow: hidden;
}

.galaxyai-compact {
    height: 100vh;

    .chat-messages {
        padding: 0.75rem 1rem;
    }

    .galaxyai-footer {
        padding: 0.5rem 0.75rem;
    }
}

.galaxyai-docked,
.galaxyai-panel {
    height: 100%;
    border-radius: 0;
}

.galaxyai-header-docked {
    padding: 0.5rem 0.75rem;
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

.galaxyai-header {
    container-type: inline-size;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    row-gap: 0.375rem;
    padding: 1rem 1.25rem;
    background: $panel-bg-color;
    border-bottom: $border-default;

    :deep(.heading) {
        margin-bottom: 0;
        white-space: nowrap;
        flex-shrink: 0;
    }

    :deep(.chat-panel-actions) {
        margin-left: auto;
    }
}

@container (max-width: 360px) {
    :deep(.heading-label) {
        display: none;
    }
}

.galaxyai-footer {
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
