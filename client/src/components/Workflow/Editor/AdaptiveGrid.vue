<script setup lang="ts">
import { useAnimationFrame } from "@/composables/sensors/animationFrame";
import type { UseElementBoundingReturn } from "@vueuse/core";
import { computed, ref, type Ref } from "vue";

const props = defineProps<{
    viewportBounds: UseElementBoundingReturn;
    viewportPan: { x: number; y: number };
    viewportScale: number;
}>();

//tmp
props;

const canvas: Ref<HTMLCanvasElement | null> = ref(null);
const context = computed(() => canvas.value?.getContext("2d") ?? null);

let redraw = true;

useAnimationFrame(() => {
    const ctx = context.value;

    if (ctx && redraw) {
        ctx.canvas.width = ctx.canvas.offsetWidth;
        ctx.canvas.height = ctx.canvas.offsetHeight;

        renderGrid(ctx);

        redraw = false;
    }
});

function renderGrid(ctx: CanvasRenderingContext2D) {}
</script>

<template>
    <canvas ref="canvas" class="adaptive-grid-canvas"></canvas>
</template>

<style scoped lang="scss">
.adaptive-grid-canvas {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    height: 100%;
}
</style>
