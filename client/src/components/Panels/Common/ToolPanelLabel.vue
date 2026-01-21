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
const description = computed(() => props.definition.description || undefined);
const isFavoritesDivider = computed(() => favoritesLabelIds.has(props.definition.id));
const isRecentLabel = computed(() => props.definition.id === RECENT_TOOLS_LABEL_ID);
const isCollapsible = computed(() => collapsibleLabelIds.has(props.definition.id) && props.collapsed !== undefined);
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
        :class="['tool-panel-label', 'tool-panel-divider', { 'tool-panel-label-clickable': isCollapsible }]"
        :tabindex="isCollapsible ? 0 : undefined"
        :title="description"
        :role="isCollapsible ? 'button' : undefined"
        :aria-expanded="isCollapsible ? !isCollapsed : undefined"
        v-on="isCollapsible ? { click: onToggle, keydown: onKeydown } : {}">
        <span class="tool-panel-label-divider-text tool-panel-divider-text">
            <FontAwesomeIcon
                v-if="isCollapsible"
                :icon="toggleIcon"
                class="tool-panel-label-toggle tool-panel-divider-toggle" />
            <FontAwesomeIcon
                v-if="isFavoritesDivider"
                :icon="faStar"
                class="tool-panel-label-divider-icon tool-panel-divider-icon" />
            {{ definition.text }}
            <GButton
                v-if="isRecentLabel"
                class="tool-panel-label-divider-action tool-panel-divider-action"
                size="small"
                color="grey"
                icon-only
                transparent
                title="Clear recent tools"
                data-description="clear-recent-tools"
                @click.stop="clearRecentTools">
                <FontAwesomeIcon :icon="faBroom" />
            </GButton>
            <ToolPanelLinks :links="definition.links || undefined" />
        </span>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";
@import "@/style/scss/tool-panel-divider.scss";

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

.tool-panel-label-clickable {
    cursor: pointer;
    user-select: none;
}
</style>
