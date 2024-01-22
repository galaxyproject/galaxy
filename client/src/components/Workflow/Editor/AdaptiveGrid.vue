<script setup lang="ts">
import type { UseElementBoundingReturn } from "@vueuse/core";
import { computed, onMounted, type Ref, ref, watch } from "vue";

import { useAnimationFrame } from "@/composables/sensors/animationFrame";

import { type AxisAlignedBoundingBox, Transform } from "./modules/geometry";

const lineGap = 10;

const landmarkLines = [
    {
        condition: (zoom: number) => zoom > 0.15,
        frequency: 10,
        width: 1,
    },
    {
        condition: (_zoom: number) => true,
        frequency: 20,
        width: 2,
    },
    {
        condition: (zoom: number) => zoom <= 0.5,
        frequency: 100,
        width: 4,
    },
    {
        condition: (zoom: number) => zoom <= 0.2,
        frequency: 200,
        width: 8,
    },
] as const;

const props = defineProps<{
    viewportBounds: UseElementBoundingReturn;
    viewportBoundingBox: AxisAlignedBoundingBox;
    transform: { x: number; y: number; k: number };
}>();

const colors = {
    grid: "black",
    landmark: "black",
};

onMounted(() => {
    const element = canvas.value!;
    const style = getComputedStyle(element);

    colors.grid = style.getPropertyValue("--grid-color");
    colors.landmark = style.getPropertyValue("--landmark-color");
});

const canvas: Ref<HTMLCanvasElement | null> = ref(null);
const context = computed(() => canvas.value?.getContext("2d") ?? null);

let redraw = true;

watch(
    () => [props.transform, props.viewportBounds],
    () => (redraw = true),
    { deep: true }
);

useAnimationFrame(() => {
    const ctx = context.value;

    if (ctx && redraw) {
        ctx.canvas.width = ctx.canvas.offsetWidth;
        ctx.canvas.height = ctx.canvas.offsetHeight;
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.resetTransform();

        new Transform().scale([props.transform.k, props.transform.k]).applyToContext(ctx);

        renderGrid(ctx);

        redraw = false;
    }
});

function renderGrid(ctx: CanvasRenderingContext2D) {
    const zoom = props.transform.k;

    const pan = {
        x: props.transform.x / zoom,
        y: props.transform.y / zoom,
    } as const;

    // standard lines
    if (zoom > 0.5) {
        ctx.strokeStyle = colors.grid;
        ctx.lineWidth = 1;

        ctx.beginPath();
        traceGrid(ctx, lineGap, pan, props.viewportBoundingBox);
        ctx.stroke();
    }

    // landmark lines
    ctx.strokeStyle = colors.landmark;

    landmarkLines.forEach((landmarkLine) => {
        if (landmarkLine.condition(zoom)) {
            ctx.lineWidth = landmarkLine.width;
            const gap = lineGap * landmarkLine.frequency;

            ctx.beginPath();
            traceGrid(ctx, gap, pan, props.viewportBoundingBox);
            ctx.stroke();
        }
    });
}

/**
 * moves the contexts path along a grid with the specified parameters
 */
function traceGrid(
    ctx: CanvasRenderingContext2D,
    gap: number,
    pan: { x: number; y: number },
    bounds: AxisAlignedBoundingBox
) {
    const startOffset = {
        x: (pan.x % gap) - gap,
        y: (pan.y % gap) - gap,
    } as const;

    const xAmount = bounds.width / gap + 2;
    const yAmount = bounds.height / gap + 2;

    // vertical
    for (let i = 0; i < xAmount; i++) {
        const x = startOffset.x + i * gap;

        ctx.moveTo(x, 0);
        ctx.lineTo(x, bounds.height);
    }

    // horizontal
    for (let i = 0; i < yAmount; i++) {
        const y = startOffset.y + i * gap;

        ctx.moveTo(0, y);
        ctx.lineTo(bounds.width, y);
    }
}
</script>

<template>
    <canvas ref="canvas" class="adaptive-grid-canvas"></canvas>
</template>

<style scoped lang="scss">
@import "~bootstrap/scss/_functions.scss";
@import "theme/blue.scss";

.adaptive-grid-canvas {
    --grid-color: #{$workflow-editor-grid-color};
    --landmark-color: #{$workflow-editor-grid-color-landmark};

    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    height: 100%;

    background-color: $workflow-editor-bg;
}
</style>
