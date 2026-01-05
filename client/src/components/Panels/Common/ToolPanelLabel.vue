<script setup lang="ts">
import { faStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { ToolSectionLabel } from "@/stores/toolStore";

import ToolPanelLinks from "./ToolPanelLinks.vue";

const props = defineProps<{
    definition: ToolSectionLabel;
}>();

const FAVORITES_LABEL_ID = "favorites_results_label";
const dividerLabelIds = new Set([FAVORITES_LABEL_ID, "search_results_label"]);

const description = computed(() => props.definition.description || undefined);
const isDivider = computed(() => dividerLabelIds.has(props.definition.id));
const isFavoritesDivider = computed(() => props.definition.id === FAVORITES_LABEL_ID);
</script>

<template>
    <div
        v-b-tooltip.topright.hover.noninteractive
        :class="['tool-panel-label', { 'tool-panel-label-divider': isDivider }]"
        tabindex="0"
        :title="description">
        <span v-if="isDivider" class="tool-panel-label-divider-text">
            <FontAwesomeIcon v-if="isFavoritesDivider" :icon="faStar" class="tool-panel-label-divider-icon" />
            {{ definition.text }}
        </span>
        <template v-else>{{ definition.text }}</template>
        <ToolPanelLinks :links="definition.links || undefined" />
    </div>
</template>

<style scoped lang="scss">
.tool-panel-label {
    &:deep(.tool-panel-links) {
        display: none;
    }

    &:hover,
    &:focus,
    &:focus-within {
        &:deep(.tool-panel-links) {
            display: inline;
        }
    }
}

.tool-panel-label.tool-panel-label-divider {
    align-items: center;
    background: transparent;
    border-left: 0;
    display: flex;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    text-transform: none;

    &::before,
    &::after {
        border-bottom: 1px solid currentColor;
        content: "";
        flex: 1;
        opacity: 0.35;
    }
}

.tool-panel-label-divider-text {
    align-items: center;
    display: inline-flex;
    gap: 0.25rem;
    white-space: nowrap;
}
</style>
