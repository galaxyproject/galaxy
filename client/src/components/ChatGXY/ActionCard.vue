<template>
    <div v-if="suggestions.length > 0" class="action-card">
        <div class="action-header">Quick Actions</div>
        <div class="action-list">
            <GButton
                v-for="action in sortedSuggestions"
                :key="`${action.action_type}-${action.description}`"
                outline
                size="small"
                :color="action.priority === 1 ? 'blue' : 'grey'"
                :disabled="processingAction"
                @click="$emit('handle-action', action)">
                <FontAwesomeIcon :icon="getIcon(action.action_type)" fixed-width />
                <span>{{ action.description }}</span>
            </GButton>
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

import GButton from "@/components/BaseComponents/GButton.vue";

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

const sortedSuggestions = computed(() => {
    return [...props.suggestions].sort((a, b) => a.priority - b.priority);
});

const iconMap: Record<ActionType, IconDefinition> = {
    [ActionType.TOOL_RUN]: faPlay,
    [ActionType.SAVE_TOOL]: faSave,
    [ActionType.CONTACT_SUPPORT]: faLifeRing,
    [ActionType.REFINE_QUERY]: faPencilAlt,
    [ActionType.DOCUMENTATION]: faBook,
    [ActionType.VIEW_EXTERNAL]: faExternalLinkAlt,
    [ActionType.APPLY_PAGE_EDIT]: faPencilAlt,
    [ActionType.INSERT_PAGE_SECTION]: faPlay,
};

function getIcon(actionType: ActionType): IconDefinition {
    return iconMap[actionType] || faWrench;
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
</style>
