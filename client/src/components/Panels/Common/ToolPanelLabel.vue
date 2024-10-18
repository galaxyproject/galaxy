<script setup lang="ts">
import { computed } from "vue";

import type { ToolSectionLabel } from "@/stores/toolStoreTypes";

import ToolPanelLinks from "./ToolPanelLinks.vue";

const props = defineProps<{
    definition: ToolSectionLabel;
}>();

const description = computed(() => props.definition.description || undefined);
</script>

<template>
    <div v-b-tooltip.topright.hover.noninteractive class="tool-panel-label" tabindex="0" :title="description">
        {{ definition.text }}
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
</style>
