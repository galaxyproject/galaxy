<script setup lang="ts">
import { computed } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";

const { toolbarStore } = useWorkflowStores();

const cssVariables = computed(() => ({
    "--position-left": `${toolbarStore.boxSelectRect.x}px`,
    "--position-top": `${toolbarStore.boxSelectRect.y}px`,
    "--width": `${toolbarStore.boxSelectRect.width}px`,
    "--height": `${toolbarStore.boxSelectRect.height}px`,
}));

const visible = computed(() => toolbarStore.boxSelectRect.width !== 0 && toolbarStore.boxSelectRect.height !== 0);

const removeMode = computed(() => toolbarStore.boxSelectMode === "remove");
</script>

<template>
    <div v-show="visible" class="box-select-preview" :class="{ 'remove-mode': removeMode }" :style="cssVariables"></div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.box-select-preview {
    pointer-events: none;
    position: absolute;
    width: var(--width);
    height: var(--height);
    top: var(--position-top);
    left: var(--position-left);

    border: dashed 2px $brand-info;
    background-color: rgba($brand-info, 0.25);

    &.remove-mode {
        border-color: $brand-danger;
        background-color: rgba($brand-danger, 0.25);
    }
}
</style>
