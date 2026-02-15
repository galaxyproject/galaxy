<script setup lang="ts">
import { faThumbsDown, faThumbsUp, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { ActionSuggestion, AgentResponse, ChatMessage } from "@/composables/agentActions";

import { formatModelName, getAgentIcon, getAgentLabel, getAgentResponseOrEmpty } from "./agentTypes";

import ActionCard from "./ActionCard.vue";

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
    <div :class="['notebook-cell', props.message.role === 'user' ? 'query-cell' : 'response-cell']">
        <!-- Query cell (user input) -->
        <template v-if="props.message.role === 'user'">
            <div class="cell-label">
                <FontAwesomeIcon :icon="faUser" fixed-width />
                <span>Query</span>
            </div>
            <div class="cell-content">{{ props.message.content }}</div>
        </template>

        <!-- Response cell (assistant output) -->
        <template v-else>
            <div class="cell-label">
                <FontAwesomeIcon :icon="getAgentIcon(props.message.agentType)" fixed-width />
                <span>{{ getAgentLabel(props.message.agentType) }}</span>
                <span
                    v-if="props.message.agentResponse?.metadata?.handoff_info"
                    class="routing-badge"
                    :title="'Routed by ' + props.message.agentResponse.metadata.handoff_info.source_agent">
                    via Router
                </span>
            </div>
            <div class="cell-content">
                <!-- eslint-disable-next-line vue/no-v-html -->
                <div v-html="props.renderMarkdown(props.message.content)" />

                <!-- Action suggestions -->
                <ActionCard
                    v-if="props.message.suggestions?.length"
                    :suggestions="props.message.suggestions"
                    :processing-action="props.processingAction"
                    @handle-action="
                        (action) => emit('handle-action', action, getAgentResponseOrEmpty(props.message.agentResponse))
                    " />

                <slot name="after-content" />
            </div>
            <div v-if="!props.message.content.startsWith('❌') && !props.message.isSystemMessage" class="cell-footer">
                <div class="feedback-actions">
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
                    <span v-if="props.message.feedback" class="feedback-text">Thanks!</span>
                </div>
                <div class="response-stats">
                    <span class="stat-item" :title="'Agent: ' + getAgentLabel(props.message.agentType)">
                        <FontAwesomeIcon :icon="getAgentIcon(props.message.agentType)" fixed-width />
                        {{ getAgentLabel(props.message.agentType) }}
                    </span>
                    <span
                        v-if="props.message.agentResponse?.metadata?.model"
                        class="stat-item"
                        :title="'Model: ' + props.message.agentResponse.metadata.model">
                        {{ formatModelName(props.message.agentResponse.metadata.model) }}
                    </span>
                    <span
                        v-if="props.message.agentResponse?.metadata?.total_tokens"
                        class="stat-item"
                        title="Tokens used">
                        {{ props.message.agentResponse.metadata.total_tokens }} tokens
                    </span>
                </div>
            </div>
        </template>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

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
    justify-content: space-between;
    margin-top: 0.5rem;
    padding-left: 0.25rem;
}

.feedback-actions {
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.response-stats {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.7rem;
    color: $text-light;

    .stat-item {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
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
