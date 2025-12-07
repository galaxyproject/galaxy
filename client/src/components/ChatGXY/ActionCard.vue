<template>
    <div v-if="suggestions.length > 0" class="action-card">
        <div class="action-header">
            <strong>Suggested Actions:</strong>
        </div>
        <div class="action-list">
            <button
                v-for="action in sortedSuggestions"
                :key="`${action.action_type}-${action.description}`"
                class="btn action-button"
                :class="`btn-${getVariant(action.priority)}`"
                :disabled="processingAction"
                @click="$emit('handle-action', action)">
                <span class="action-icon">{{ getIcon(action.action_type) }}</span>
                <span class="action-text">{{ action.description }}</span>
                <span v-if="action.confidence" class="action-confidence">
                    <small>({{ action.confidence }})</small>
                </span>
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
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
    return [...props.suggestions].sort((a, b) => a.priority - b.priority);
});

function getIcon(actionType: ActionType): string {
    const icons: Partial<Record<ActionType, string>> = {
        [ActionType.TOOL_RUN]: "🔧",
        [ActionType.SAVE_TOOL]: "💾",
        [ActionType.TEST_TOOL]: "🧪",
        [ActionType.PARAMETER_CHANGE]: "⚙️",
        [ActionType.WORKFLOW_STEP]: "📊",
        [ActionType.CONTACT_SUPPORT]: "🆘",
        [ActionType.REFINE_QUERY]: "✏️",
    };
    return icons[actionType as ActionType] || "❓";
}

function getVariant(priority: number): string {
    switch (priority) {
        case 1:
            return "primary";
        case 2:
            return "secondary";
        case 3:
            return "info";
        default:
            return "light";
    }
}
</script>

<style scoped>
.action-card {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 12px;
    margin-top: 12px;
}

.action-header {
    margin-bottom: 8px;
    color: #495057;
    font-size: 0.9rem;
}

.action-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.action-button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    font-size: 0.875rem;
    border-radius: 20px;
    transition: all 0.2s ease;
}

.action-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.action-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.action-icon {
    font-size: 1rem;
}

.action-confidence {
    opacity: 0.7;
    font-style: italic;
}
</style>
