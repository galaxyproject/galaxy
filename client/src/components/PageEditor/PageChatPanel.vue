<script setup lang="ts">
/**
 * Page-specific chat panel.
 * Talks to the page_assistant agent, shows diff views for edit proposals,
 * and applies accepted edits to the page via the store.
 */
import { faBook, faHistory, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BSkeleton } from "bootstrap-vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { ChatMessage } from "@/components/ChatGXY/chatTypes";
import { generateId, scrollToBottom } from "@/components/ChatGXY/chatUtils";
import { PAGE_LABELS } from "@/components/Page/constants";
import { type AgentResponse, type EditProposal, useAgentActions } from "@/composables/agentActions";
import { useMarkdown } from "@/composables/markdown";
import { type PageEditorMode, usePageEditorStore } from "@/stores/pageEditorStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { applySectionEdit } from "./sectionDiffUtils";

import PageChatHistoryList from "./PageChatHistoryList.vue";
import ProposalDiffView from "./ProposalDiffView.vue";
import SectionPatchView from "./SectionPatchView.vue";
import ChatInput from "@/components/ChatGXY/ChatInput.vue";
import ChatMessageCell from "@/components/ChatGXY/ChatMessageCell.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = withDefaults(
    defineProps<{
        historyId?: string;
        pageId: string;
        pageContent: string;
    }>(),
    { historyId: "" },
);

const isHistoryAttached = computed(() => !!props.historyId);
const chatMode = computed<PageEditorMode>(() => (isHistoryAttached.value ? "history" : "standalone"));
const chatLabels = computed(() => PAGE_LABELS[chatMode.value]);
const assistantName = computed(() => chatLabels.value.assistantName);

const AGENT_TYPE = "page_assistant";

const store = usePageEditorStore();
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, removeNewlinesAfterList: true });
const { processingAction, handleAction } = useAgentActions();

const query = ref("");
const messages = ref<ChatMessage[]>([]);
const busy = ref(false);
const chatContainer = ref<HTMLElement>();
const currentChatId = ref<string | null>(null);
const dismissedProposals = ref(new Set<string>());

onMounted(async () => {
    await loadPageChat();

    if (messages.value.length === 0) {
        messages.value.push({
            id: generateId(),
            role: "assistant",
            content: chatLabels.value.assistantWelcome,
            timestamp: new Date(),
            agentType: AGENT_TYPE,
            confidence: "high",
            feedback: null,
            isSystemMessage: true,
        });
    }
});

async function loadPageChat() {
    store.chatError = null;

    // Try store-cached exchange ID first (avoids API round-trip on panel reopen)
    const storedExchangeId = store.getCurrentChatExchangeId(props.pageId);
    if (storedExchangeId !== null) {
        try {
            await loadConversation(storedExchangeId);
            if (messages.value.length > 0) {
                return;
            }
        } catch (e) {
            console.warn("Failed to load cached chat exchange:", e);
            store.clearCurrentChatExchangeId(props.pageId);
        }
    }

    // Fall back to API
    try {
        const { data, error } = await GalaxyApi().GET("/api/chat/page/{page_id}/history", {
            params: { path: { page_id: props.pageId }, query: { limit: 1 } },
        });

        if (data && !error && data.length > 0) {
            await loadConversation(data[0]!.id);
        }
    } catch (e) {
        console.warn("Failed to load page chat history:", e);
        store.chatError = errorMessageAsString(e);
    }
}

async function loadConversation(exchangeId: string) {
    const { data } = await GalaxyApi().GET("/api/chat/exchange/{exchange_id}/messages", {
        params: { path: { exchange_id: exchangeId } },
    });

    if (data && data.length > 0) {
        messages.value = data.map((msg: any, index: number) => {
            const m: ChatMessage = {
                id: `hist-${msg.role}-${exchangeId}-${index}`,
                role: msg.role,
                content: msg.content,
                timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
                feedback: null,
            };

            if (msg.role === "assistant") {
                m.agentType = msg.agent_type || AGENT_TYPE;
                m.confidence = msg.agent_response?.confidence || "medium";
                m.feedback = msg.feedback === 1 ? "up" : msg.feedback === 0 ? "down" : null;
                if (msg.agent_response) {
                    m.agentResponse = msg.agent_response;
                    m.suggestions = msg.agent_response.suggestions || [];
                }
            }

            return m;
        });
        currentChatId.value = exchangeId;
        store.setCurrentChatExchangeId(props.pageId, exchangeId);
        dismissedProposals.value = new Set(store.getDismissedProposals(props.pageId));
    }
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

    const wasNewExchange = currentChatId.value === null;

    try {
        const { data, error } = await GalaxyApi().POST("/api/chat", {
            params: { query: { agent_type: AGENT_TYPE } },
            body: {
                query: currentQuery,
                context: null,
                exchange_id: currentChatId.value,
                page_id: props.pageId,
            },
        });

        if (error) {
            const errStr = errorMessageAsString(error, "Failed to get response.");
            messages.value.push({
                id: generateId(),
                role: "assistant",
                content: `Error: ${errStr}`,
                timestamp: new Date(),
                agentType: AGENT_TYPE,
                confidence: "low",
                feedback: null,
            });
        } else if (data) {
            if (data.exchange_id) {
                currentChatId.value = data.exchange_id;
                store.setCurrentChatExchangeId(props.pageId, data.exchange_id);
            }

            if (wasNewExchange) {
                store.loadPageChatHistory(props.pageId);
            }

            const agentResponse = data.agent_response as AgentResponse | undefined;

            messages.value.push({
                id: generateId(),
                role: "assistant",
                content: data.response || "No response received",
                timestamp: new Date(),
                agentType: agentResponse?.agent_type || AGENT_TYPE,
                confidence: agentResponse?.confidence || "medium",
                feedback: null,
                agentResponse: agentResponse,
                suggestions: agentResponse?.suggestions || [],
            });
        }
    } catch (e) {
        messages.value.push({
            id: generateId(),
            role: "assistant",
            content: "Unexpected error occurred. Please try again.",
            timestamp: new Date(),
            agentType: AGENT_TYPE,
            confidence: "low",
            feedback: null,
        });
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
    if (!message || !currentChatId.value) {
        return;
    }
    message.feedback = value;
    try {
        const feedbackValue = value === "up" ? 1 : 0;
        const { error } = await GalaxyApi().PUT("/api/chat/exchange/{exchange_id}/feedback", {
            params: { path: { exchange_id: currentChatId.value } },
            body: feedbackValue,
        });
        if (error) {
            message.feedback = null;
        }
    } catch {
        message.feedback = null;
    }
}

function djb2Hash(s: string): string {
    let h = 5381;
    for (let i = 0; i < s.length; i++) {
        h = (h * 33 + s.charCodeAt(i)) >>> 0;
    }
    return h.toString(16).padStart(8, "0");
}

function isProposalStale(msg: ChatMessage): boolean {
    const meta = msg.agentResponse?.metadata;
    const originalHash = meta?.original_content_hash as string | undefined;
    if (!originalHash) {
        return false;
    }
    return originalHash !== djb2Hash(props.pageContent);
}

function getEditProposal(msg: ChatMessage): EditProposal | null {
    const meta = msg.agentResponse?.metadata;
    const editMode = meta?.edit_mode as EditProposal["mode"] | undefined;
    if (!editMode) {
        return null;
    }
    return {
        mode: editMode,
        content: (meta?.content as string) || (meta?.new_section_content as string) || "",
        target_section_heading: meta?.target_section_heading as string | undefined,
        new_section_content: meta?.new_section_content as string | undefined,
    };
}

function isProposalVisible(msg: ChatMessage): boolean {
    if (dismissedProposals.value.has(msg.id)) {
        return false;
    }
    const proposal = getEditProposal(msg);
    if (!proposal) {
        return false;
    }
    // Content-based: if full_replacement content matches current doc, already applied
    if (proposal.mode === "full_replacement" && proposal.content === props.pageContent) {
        return false;
    }
    return true;
}

function getProposalMode(msg: ChatMessage): string {
    return getEditProposal(msg)?.mode || "";
}

function buildProposedContent(msg: ChatMessage): string {
    const proposal = getEditProposal(msg);
    if (!proposal) {
        return props.pageContent;
    }
    if (proposal.mode === "full_replacement") {
        return proposal.content;
    }
    // section_patch: reconstruct full doc by replacing the target section
    return applySectionEdit(
        props.pageContent,
        proposal.target_section_heading || "",
        proposal.new_section_content || proposal.content,
    );
}

async function applyFullReplacement(msg: ChatMessage) {
    const proposal = getEditProposal(msg);
    if (!proposal) {
        return;
    }
    store.updateContent(proposal.content);
    await store.savePage("agent");
    dismissedProposals.value.add(msg.id);
    store.addDismissedProposal(props.pageId, msg.id);
}

async function applySectionPatched(patchedContent: string, msg: ChatMessage) {
    store.updateContent(patchedContent);
    await store.savePage("agent");
    dismissedProposals.value.add(msg.id);
    store.addDismissedProposal(props.pageId, msg.id);
}

function dismissProposal(msg: ChatMessage) {
    dismissedProposals.value.add(msg.id);
    store.addDismissedProposal(props.pageId, msg.id);
}

function toggleHistory() {
    store.toggleChatHistory();
    if (store.showChatHistory) {
        store.loadPageChatHistory(props.pageId);
    }
}

async function handleHistorySelect(item: { id: string }) {
    try {
        await loadConversation(item.id);
        store.showChatHistory = false;
        await nextTick();
        scrollToBottom(chatContainer.value);
    } catch (e) {
        store.chatHistoryError = errorMessageAsString(e);
    }
}

function resetToNewChat() {
    messages.value = [
        {
            id: generateId(),
            role: "assistant",
            content: chatLabels.value.newConversation,
            timestamp: new Date(),
            agentType: AGENT_TYPE,
            confidence: "high",
            feedback: null,
            isSystemMessage: true,
        },
    ];
    currentChatId.value = null;
    store.setCurrentChatExchangeId(props.pageId, null);
    query.value = "";
    dismissedProposals.value = new Set();
    store.clearDismissedProposals(props.pageId);
}

async function handleHistoryDelete(ids: string[]) {
    try {
        await store.deletePageChatExchanges(props.pageId, ids);
        if (currentChatId.value && ids.includes(currentChatId.value)) {
            resetToNewChat();
        }
    } catch (e) {
        store.chatHistoryError = errorMessageAsString(e);
    }
}

async function deleteCurrentExchange() {
    if (!currentChatId.value) {
        return;
    }
    try {
        await store.deletePageChatExchanges(props.pageId, [currentChatId.value]);
        resetToNewChat();
    } catch (e) {
        store.chatError = errorMessageAsString(e);
    }
}

function startNewConversation() {
    resetToNewChat();
}
</script>

<template>
    <div class="page-chat-panel d-flex flex-column h-100" data-description="page chat panel">
        <div class="chat-panel-header d-flex align-items-center justify-content-between p-2 border-bottom">
            <span class="d-flex align-items-center gap-2">
                <FontAwesomeIcon :icon="faBook" fixed-width />
                <strong>{{ assistantName }}</strong>
            </span>
            <span class="d-flex align-items-center gap-1">
                <BButton
                    variant="outline-secondary"
                    size="sm"
                    :pressed="store.showChatHistory"
                    data-description="chat history button"
                    @click="toggleHistory">
                    <FontAwesomeIcon :icon="faHistory" fixed-width />
                </BButton>
                <BButton
                    v-if="currentChatId"
                    variant="outline-danger"
                    size="sm"
                    title="Delete current conversation"
                    data-description="delete conversation button"
                    @click="deleteCurrentExchange">
                    <FontAwesomeIcon :icon="faTrash" fixed-width />
                </BButton>
                <BButton
                    variant="outline-primary"
                    size="sm"
                    data-description="new conversation button"
                    @click="startNewConversation">
                    New Chat
                </BButton>
            </span>
        </div>

        <div class="chat-body d-flex flex-grow-1" style="min-height: 0">
            <div ref="chatContainer" class="chat-panel-messages flex-grow-1 overflow-auto">
                <BAlert
                    v-if="store.chatError"
                    variant="danger"
                    dismissible
                    show
                    data-description="chat error alert"
                    @dismissed="store.chatError = null">
                    {{ store.chatError }}
                </BAlert>

                <ChatMessageCell
                    v-for="msg in messages"
                    :key="msg.id"
                    :message="msg"
                    :render-markdown="renderMarkdown"
                    :processing-action="processingAction"
                    @feedback="sendFeedback"
                    @handle-action="handleAction">
                    <template v-if="isProposalVisible(msg)" v-slot:after-content>
                        <ProposalDiffView
                            v-if="getProposalMode(msg) === 'full_replacement'"
                            :original="pageContent"
                            :proposed="buildProposedContent(msg)"
                            :stale="isProposalStale(msg)"
                            @accept="applyFullReplacement(msg)"
                            @reject="dismissProposal(msg)" />
                        <SectionPatchView
                            v-else-if="getProposalMode(msg) === 'section_patch'"
                            :original="pageContent"
                            :proposed="buildProposedContent(msg)"
                            :stale="isProposalStale(msg)"
                            @accept="applySectionPatched($event, msg)"
                            @reject="dismissProposal(msg)" />
                    </template>
                </ChatMessageCell>

                <div v-if="busy" class="loading-cell" data-description="chat loading indicator">
                    <div class="cell-label">
                        <FontAwesomeIcon :icon="faBook" fixed-width />
                        <span>{{ assistantName }}</span>
                    </div>
                    <div class="cell-content">
                        <BSkeleton animation="wave" width="85%" />
                        <BSkeleton animation="wave" width="55%" />
                        <BSkeleton animation="wave" width="70%" />
                    </div>
                </div>

                <div v-if="!busy && messages.length === 0" class="text-muted text-center p-4">
                    <LoadingSpan message="Loading conversation..." />
                </div>
            </div>

            <PageChatHistoryList
                v-if="store.showChatHistory"
                class="chat-history-sidebar border-left"
                :items="store.pageChatHistory"
                :is-loading="store.isLoadingChatHistory"
                :error="store.chatHistoryError"
                :active-exchange-id="currentChatId"
                data-description="chat history sidebar"
                @select="handleHistorySelect"
                @delete="handleHistoryDelete"
                @dismiss-error="store.chatHistoryError = null" />
        </div>

        <div class="chat-panel-footer p-2 border-top">
            <ChatInput v-model="query" :busy="busy" :placeholder="chatLabels.chatPlaceholder" @submit="submitQuery" />
        </div>
    </div>
</template>

<style scoped>
.page-chat-panel {
    background: var(--body-bg, #fff);
    min-width: 0;
}

.chat-panel-header {
    background: var(--panel-header-bg, #f8f9fa);
    font-size: 0.85rem;
}

.chat-panel-header .gap-2 {
    gap: 0.5rem;
}

.chat-panel-messages {
    padding: 0.75rem;
    min-width: 0;
}

.chat-history-sidebar {
    width: 220px;
    flex-shrink: 0;
    overflow-y: auto;
}

.chat-panel-footer {
    background: var(--panel-header-bg, #f8f9fa);
}

.loading-cell {
    margin-bottom: 1rem;
    opacity: 0.7;
}

.loading-cell .cell-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.025em;
    margin-bottom: 0.375rem;
    padding-left: 0.25rem;
    color: var(--text-muted, #6c757d);
}

.loading-cell .cell-content {
    border-left: 3px solid var(--brand-secondary, #6c757d);
    background: var(--panel-bg-color, #f8f9fa);
    padding: 0.75rem 1rem;
    border-radius: 4px;
}
</style>
