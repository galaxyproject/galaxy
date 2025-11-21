<template>
    <div v-if="suggestions.length > 0" class="action-card">
        <div class="action-header">Suggested Actions</div>
        <div class="action-list">
            <button
                v-for="(action, index) in sortedSuggestions"
                :key="`${action.action_type}-${index}-${action.description}`"
                class="btn action-button"
                :class="getButtonClass(action.priority)"
                :disabled="processingAction"
                @click="$emit('handle-action', action)">
                <FontAwesomeIcon :icon="getIcon(action.action_type)" fixed-width />
                <span class="action-text">{{ action.description }}</span>
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
    faBook,
    faExternalLinkAlt,
    faLifeRing,
    faPencilAlt,
    faPlay,
    faSave,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { type ActionSuggestion, ActionType } from "@/composables/agentActions";

interface Props {
    suggestions: ActionSuggestion[];
    processingAction?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    processingAction: false,
});

defineEmits<{
    "handle-action": [action: ActionSuggestion];
}>();

// Sort suggestions by priority (1 = highest)
const sortedSuggestions = computed(() => {
    return [...props.suggestions]
        .filter((suggestion) => suggestion.action_type !== ActionType.PYODIDE_EXECUTE)
        .sort((a, b) => a.priority - b.priority);
});

const iconMap: Record<ActionType, IconDefinition> = {
    [ActionType.TOOL_RUN]: faPlay,
    [ActionType.SAVE_TOOL]: faSave,
    [ActionType.CONTACT_SUPPORT]: faLifeRing,
    [ActionType.REFINE_QUERY]: faPencilAlt,
    [ActionType.DOCUMENTATION]: faBook,
    [ActionType.VIEW_EXTERNAL]: faExternalLinkAlt,
};

function getIcon(actionType: ActionType): IconDefinition {
    return iconMap[actionType] || faWrench;
}

function getButtonClass(priority: number): string {
    switch (priority) {
        case 1:
            return "btn-outline-primary";
        case 2:
            return "btn-outline-secondary";
        default:
            return "btn-outline-secondary";
    }
}
</script>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.action-card {
    background: $white;
    border: $border-default;
    border-radius: $border-radius-base;
    padding: 0.75rem;
    margin-top: 0.75rem;
}

.action-header {
    font-size: 0.75rem;
    font-weight: 600;
    color: $text-muted;
    text-transform: uppercase;
    letter-spacing: 0.025em;
    margin-bottom: 0.5rem;
}

.action-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.action-button {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    font-size: 0.8rem;
    border-radius: $border-radius-large;
    transition: all 0.15s ease;

    &:hover:not(:disabled) {
        transform: translateY(-1px);
    }

    &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
}

.action-text {
    white-space: nowrap;
}
</style>
