<script setup lang="ts">
/**
 * Two-pane split layout with a draggable resize handle.
 *
 * Composes ``DraggableSeparator`` for the divider, inheriting its
 * keyboard accessibility, hover-delay, and animation-frame throttling.
 * Caller supplies the pane content via ``left``/``right`` slots.
 */
import { useElementBounding } from "@vueuse/core";
import { computed, ref, watch } from "vue";

import DraggableSeparator from "@/components/Common/DraggableSeparator.vue";

const props = withDefaults(
    defineProps<{
        /** Starting size of the left pane, as a percent of the container. */
        initialSplit?: number;
        /** Smallest left-pane size, as a percent of the container. */
        minPercent?: number;
        /** Largest left-pane size, as a percent of the container. */
        maxPercent?: number;
    }>(),
    {
        initialSplit: 60,
        minPercent: 20,
        maxPercent: 80,
    },
);

const containerRef = ref<HTMLElement>();
const { width: containerWidth } = useElementBounding(containerRef);

// Position is the left-pane width in pixels; ``DraggableSeparator`` works in
// pixels so this is the natural shape and avoids percent<->px drift.
const leftWidthPx = ref(0);
let initialized = false;

watch(
    containerWidth,
    (w) => {
        if (!w) {
            return;
        }
        if (!initialized) {
            leftWidthPx.value = (props.initialSplit / 100) * w;
            initialized = true;
        } else {
            const minPx = (props.minPercent / 100) * w;
            const maxPx = (props.maxPercent / 100) * w;
            leftWidthPx.value = Math.min(Math.max(leftWidthPx.value, minPx), maxPx);
        }
    },
    { immediate: true },
);

const minPx = computed(() => (containerWidth.value * props.minPercent) / 100);
const maxPx = computed(() => (containerWidth.value * props.maxPercent) / 100);
const rightWidthPx = computed(() => Math.max(containerWidth.value - leftWidthPx.value, 0));
</script>

<template>
    <div ref="containerRef" class="split-view" data-description="split view">
        <div class="split-pane" :style="{ flexBasis: `${leftWidthPx}px` }">
            <slot name="left" />
        </div>
        <DraggableSeparator
            :position="leftWidthPx"
            side="left"
            :inner="true"
            :min="minPx"
            :max="maxPx"
            @positionChanged="(v) => (leftWidthPx = v)" />
        <div class="split-pane" :style="{ flexBasis: `${rightWidthPx}px` }">
            <slot name="right" />
        </div>
    </div>
</template>

<style scoped>
.split-view {
    display: flex;
    flex: 1;
    overflow: hidden;
    min-height: 0;
    position: relative;
}

.split-pane {
    overflow: auto;
    min-width: 0;
}
</style>
