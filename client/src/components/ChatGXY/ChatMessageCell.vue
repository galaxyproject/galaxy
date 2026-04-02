<script setup lang="ts">
import { faThumbsDown, faThumbsUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { ActionSuggestion, AgentResponse } from "@/composables/agentActions";

import { formatModelName, getAgentIcon, getAgentLabel, getAgentResponseOrEmpty } from "./agentTypes";
import type { ChatMessage } from "./chatTypes";

import ActionCard from "./ActionCard.vue";

const MENTION_RE = /@(dataset|history):(\S+)/g;

function escapeHtml(str: string): string {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function renderEntityRefs(text: string): string {
    return text.replace(MENTION_RE, (_match, type: string, identifier: string) => {
        const safeType = escapeHtml(type);
        const safeId = escapeHtml(identifier);
        const icon = type === "dataset" ? "&#xf1c0;" : "&#xf1da;";
        return `<span class="entity-ref" title="${safeType} ${safeId}"><span class="entity-ref-icon">${icon}</span>@${safeType}:${safeId}</span>`;
    });
}

const props = defineProps<{
    message: ChatMessage;
    renderMarkdown: (text: string) => string;
    processingAction: boolean;
}>();

const emit = defineEmits<{
    (e: "feedback", messageId: string, value: "up" | "down"): void;
    (e: "handle-action", action: ActionSuggestion, agentResponse: AgentResponse): void;
}>();
</script>

<template>
    <div
        :class="[
            'exchange-entry',
            props.message.role === 'user' ? 'entry-query' : 'entry-response',
            { 'entry-system': props.message.isSystemMessage },
        ]">
        <!-- System/welcome messages -->
        <template v-if="props.message.isSystemMessage">
            <div class="system-notice">{{ props.message.content }}</div>
        </template>

        <!-- User query -->
        <template v-else-if="props.message.role === 'user'">
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="query-text" v-html="renderEntityRefs(props.message.content)" />
        </template>

        <!-- Assistant response -->
        <template v-else>
            <div class="response-body">
                <div class="response-gutter">
                    <span class="agent-indicator" :title="getAgentLabel(props.message.agentType)">
                        <FontAwesomeIcon :icon="getAgentIcon(props.message.agentType)" fixed-width />
                    </span>
                </div>
                <div class="response-main">
                    <!-- eslint-disable-next-line vue/no-v-html -->
                    <div class="response-content" v-html="props.renderMarkdown(props.message.content)" />

                    <ActionCard
                        v-if="props.message.suggestions?.length"
                        :suggestions="props.message.suggestions"
                        :processing-action="props.processingAction"
                        @handle-action="
                            (action) =>
                                emit('handle-action', action, getAgentResponseOrEmpty(props.message.agentResponse))
                        " />

                    <slot name="after-content" />

                    <div v-if="!props.message.content.startsWith('❌')" class="response-meta">
                        <div class="meta-left">
                            <button
                                class="feedback-btn"
                                :disabled="props.message.feedback !== null"
                                :class="{ active: props.message.feedback === 'up' }"
                                title="Helpful"
                                @click="emit('feedback', props.message.id, 'up')">
                                <FontAwesomeIcon :icon="faThumbsUp" fixed-width />
                            </button>
                            <button
                                class="feedback-btn"
                                :disabled="props.message.feedback !== null"
                                :class="{ active: props.message.feedback === 'down' }"
                                title="Not helpful"
                                @click="emit('feedback', props.message.id, 'down')">
                                <FontAwesomeIcon :icon="faThumbsDown" fixed-width />
                            </button>
                            <span v-if="props.message.feedback" class="feedback-ack">Thanks!</span>
                        </div>
                        <div class="meta-right">
                            <span class="meta-tag">{{ getAgentLabel(props.message.agentType) }}</span>
                            <span v-if="props.message.agentResponse?.metadata?.model" class="meta-tag">
                                {{ formatModelName(props.message.agentResponse.metadata.model) }}
                            </span>
                            <span v-if="props.message.agentResponse?.metadata?.total_tokens" class="meta-tag">
                                {{ props.message.agentResponse.metadata.total_tokens }} tok
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </template>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.exchange-entry {
    animation: entryReveal 0.25s ease-out both;

    & + & {
        margin-top: 1.25rem;
    }
}

// --- System messages: centered, quiet ---
.system-notice {
    text-align: center;
    font-size: 0.8rem;
    color: $text-light;
    padding: 0.75rem 2rem;
    position: relative;

    &::before,
    &::after {
        content: "";
        position: absolute;
        top: 50%;
        width: 2rem;
        height: 1px;
        background: $border-color;
    }

    &::before {
        right: calc(100% - 2rem);
        left: 0;
    }

    &::after {
        left: calc(100% - 2rem);
        right: 0;
    }
}

// --- User query: lightweight prompt marker ---
.entry-query {
    .query-text {
        font-size: 0.925rem;
        color: $text-color;
        padding: 0.5rem 0.75rem;
        border-left: 2px solid $brand-primary;
        margin-left: 0.25rem;
    }
}

// --- Assistant response: the main content ---
.response-body {
    display: flex;
    gap: 0;
}

.response-gutter {
    flex-shrink: 0;
    width: 2rem;
    padding-top: 0.125rem;
}

.agent-indicator {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    background: rgba($brand-primary, 0.08);
    color: $brand-primary;
    font-size: 0.65rem;
    cursor: default;
}

.response-main {
    flex: 1;
    min-width: 0;
}

.response-content {
    line-height: 1.65;
    color: $text-color;

    :deep(p:first-child) {
        margin-top: 0;
    }

    :deep(p:last-child) {
        margin-bottom: 0;
    }

    :deep(code) {
        background: rgba($brand-dark, 0.06);
        padding: 0.1rem 0.35rem;
        border-radius: $border-radius-base;
        font-family: $font-family-monospace;
        font-size: 0.84em;
    }

    :deep(pre) {
        background: darken($white, 1%);
        border: $border-default;
        padding: 0.75rem;
        border-radius: $border-radius-base;
        overflow-x: auto;
        margin: 0.625rem 0;

        code {
            background: none;
            padding: 0;
        }
    }

    :deep(ul),
    :deep(ol) {
        margin-bottom: 0.625rem;
        padding-left: 1.5rem;
    }

    :deep(li) {
        margin-bottom: 0.2rem;
    }

    :deep(h1),
    :deep(h2),
    :deep(h3),
    :deep(h4) {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-weight: 600;

        &:first-child {
            margin-top: 0;
        }
    }

    :deep(table) {
        width: 100%;
        border-collapse: collapse;
        margin: 0.625rem 0;
        font-size: 0.85em;

        th,
        td {
            padding: 0.375rem 0.625rem;
            border: $border-default;
            text-align: left;
        }

        th {
            background: $panel-bg-color;
            font-weight: 600;
        }
    }

    :deep(blockquote) {
        border-left: 2px solid $border-color;
        padding-left: 0.75rem;
        color: $text-muted;
        margin: 0.625rem 0;
    }
}

// --- Footer metadata: compact, secondary ---
.response-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 0.625rem;
    padding-top: 0.5rem;
    border-top: 1px solid rgba($border-color, 0.5);
}

.meta-left {
    display: flex;
    align-items: center;
    gap: 0.125rem;
}

.meta-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.meta-tag {
    font-size: 0.675rem;
    color: $text-light;
    letter-spacing: 0.01em;
}

.feedback-btn {
    background: none;
    border: none;
    padding: 0.2rem 0.375rem;
    color: $text-light;
    cursor: pointer;
    border-radius: $border-radius-base;
    font-size: 0.75rem;
    transition:
        color 0.15s,
        background 0.15s;

    &:hover:not(:disabled) {
        color: $brand-primary;
        background: rgba($brand-primary, 0.06);
    }

    &:disabled {
        cursor: default;
        opacity: 0.4;
    }

    &.active {
        color: $brand-success;
        opacity: 1;
    }
}

.feedback-ack {
    font-size: 0.675rem;
    color: $text-light;
    margin-left: 0.25rem;
}

// --- Animation ---
@keyframes entryReveal {
    from {
        opacity: 0;
        transform: translateY(6px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@media (prefers-reduced-motion: reduce) {
    .exchange-entry {
        animation: none;
    }
}

// --- Entity references in user messages ---
.query-text :deep(.entity-ref) {
    display: inline;
    background: rgba($brand-primary, 0.1);
    color: $brand-primary;
    padding: 0.1rem 0.35rem;
    border-radius: $border-radius-base;
    font-family: $font-family-monospace;
    font-size: 0.88em;
    white-space: nowrap;
    cursor: default;
}

.query-text :deep(.entity-ref-icon) {
    font-family: "Font Awesome 5 Free", "Font Awesome 6 Free";
    font-weight: 900;
    font-size: 0.75em;
    margin-right: 0.2rem;
}
</style>
