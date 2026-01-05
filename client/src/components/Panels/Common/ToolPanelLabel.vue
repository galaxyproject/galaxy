<script setup lang="ts">
import { faBroom, faChevronDown, faChevronRight, faStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { ToolSectionLabel } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import ToolPanelLinks from "./ToolPanelLinks.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps<{
    definition: ToolSectionLabel;
    collapsed?: boolean;
}>();

const emit = defineEmits<{
    (e: "toggle", labelId: string): void;
}>();

const FAVORITES_RESULTS_LABEL_ID = "favorites_results_label";
const FAVORITES_LABEL_ID = "favorites_label";
const RECENT_TOOLS_LABEL_ID = "recent_tools_label";
const favoritesLabelIds = new Set([FAVORITES_RESULTS_LABEL_ID, FAVORITES_LABEL_ID]);
const collapsibleLabelIds = new Set([FAVORITES_RESULTS_LABEL_ID, FAVORITES_LABEL_ID, RECENT_TOOLS_LABEL_ID]);
const dividerLabelIds = new Set([
    FAVORITES_RESULTS_LABEL_ID,
    FAVORITES_LABEL_ID,
    RECENT_TOOLS_LABEL_ID,
    "search_results_label",
]);

const description = computed(() => props.definition.description || undefined);
const isDivider = computed(() => dividerLabelIds.has(props.definition.id));
const isFavoritesDivider = computed(() => favoritesLabelIds.has(props.definition.id));
const isRecentLabel = computed(() => props.definition.id === RECENT_TOOLS_LABEL_ID);
const isCollapsible = computed(
    () => collapsibleLabelIds.has(props.definition.id) && props.collapsed !== undefined,
);
const isCollapsed = computed(() => props.collapsed ?? false);
const toggleIcon = computed(() => (isCollapsed.value ? faChevronRight : faChevronDown));

const { clearRecentTools } = useUserStore();

function onToggle() {
    if (isCollapsible.value) {
        emit("toggle", props.definition.id);
    }
}

function onKeydown(event: KeyboardEvent) {
    if (!isCollapsible.value) {
        return;
    }
    if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        emit("toggle", props.definition.id);
    }
}
</script>

<template>
    <div
        v-b-tooltip.topright.hover.noninteractive
        :class="[
            'tool-panel-label',
            {
                'tool-panel-label-divider': isDivider,
                'tool-panel-label-actionable': isRecentLabel && !isDivider,
                'tool-panel-label-clickable': isCollapsible,
            },
        ]"
        tabindex="0"
        :title="description"
        :role="isCollapsible ? 'button' : undefined"
        :aria-expanded="isCollapsible ? !isCollapsed : undefined"
        @click="onToggle"
        @keydown="onKeydown">
        <span v-if="isDivider" class="tool-panel-label-divider-text">
            <FontAwesomeIcon v-if="isCollapsible" :icon="toggleIcon" class="tool-panel-label-toggle" />
            <FontAwesomeIcon v-if="isFavoritesDivider" :icon="faStar" class="tool-panel-label-divider-icon" />
            {{ definition.text }}
            <GButton
                v-if="isRecentLabel"
                class="tool-panel-label-divider-action"
                size="small"
                color="grey"
                icon-only
                transparent
                title="Clear recent tools"
                data-description="clear-recent-tools"
                @click.stop="clearRecentTools">
                <FontAwesomeIcon :icon="faBroom" />
            </GButton>
        </span>
        <template v-else>
            <span>
                <FontAwesomeIcon v-if="isCollapsible" :icon="toggleIcon" class="tool-panel-label-toggle" />
                {{ definition.text }}
            </span>
            <GButton
                v-if="isRecentLabel"
                class="tool-panel-label-action"
                size="small"
                color="grey"
                icon-only
                transparent
                title="Clear recent tools"
                data-description="clear-recent-tools"
                @click.stop="clearRecentTools">
                <FontAwesomeIcon :icon="faBroom" />
            </GButton>
        </template>
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
    gap: 0.5rem;
    white-space: nowrap;
}

.tool-panel-label-actionable {
    align-items: center;
    display: flex;
    gap: 0.5rem;
    justify-content: space-between;
}

.tool-panel-label-action {
    margin-left: auto;
}

.tool-panel-label-divider-action {
    margin-left: 0;
}

.tool-panel-label-toggle {
    opacity: 0.8;
}

.tool-panel-label-clickable {
    cursor: pointer;
    user-select: none;
}
</style>
