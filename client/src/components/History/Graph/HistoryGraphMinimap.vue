<script setup lang="ts">
import type { Ref } from "vue";
import { computed, onMounted, ref, toRef, watch } from "vue";

import type { GraphLayout } from "@/components/Graph/types";
import { useAnimationFrame } from "@/composables/sensors/animationFrame";
import { useMinimapInteraction } from "@/composables/useMinimapInteraction";
import { AxisAlignedBoundingBox } from "@/utils/geometry";

// Colors resolved once at mount from CSS custom properties on the canvas element.
// Uses brand-primary for nodes (set via SCSS in the scoped style block).
let nodeColor = "#000";
let viewColor = "rgba(0, 0, 0, 0.2)";
let viewOutlineColor = "#000";

const props = withDefaults(
    defineProps<{
        layout: GraphLayout | null;
        viewportBoundingBox: AxisAlignedBoundingBox;
        selectedNodeId?: string | null;
        parentRight: number;
        parentBottom: number;
    }>(),
    {
        selectedNodeId: null,
    },
);

const emit = defineEmits<{
    (e: "panBy", offset: { x: number; y: number }): void;
    (e: "moveTo", position: { x: number; y: number }): void;
}>();

const canvas: Ref<HTMLCanvasElement | null> = ref(null);
const minimap: Ref<HTMLElement | null> = ref(null);
let redraw = false;

const MINIMAP_SIZE = 150;
const MINIMAP_MIN = 50;
const MINIMAP_MAX = 300;
const MINIMAP_PADDING = 7;
const MINIMAP_BORDER = 1;

// ── Content bounds from layout ──

const contentBounds = computed(() => {
    const aabb = new AxisAlignedBoundingBox();
    if (props.layout) {
        for (const node of props.layout.nodes) {
            aabb.fitRectangle({ x: node.x, y: node.y, width: node.width, height: node.height });
        }
        aabb.squareCenter();
        aabb.expand(60);
    }
    return aabb;
});

const viewportBoundsRef = toRef(props, "viewportBoundingBox");
const parentRightRef = toRef(props, "parentRight");
const parentBottomRef = toRef(props, "parentBottom");

// ── Shared interaction ──

const { getCanvasTransform, recomputeTransform, minimapSize } = useMinimapInteraction({
    canvasRef: canvas,
    containerRef: minimap,
    parentRight: parentRightRef,
    parentBottom: parentBottomRef,
    contentBounds,
    viewportBounds: viewportBoundsRef,
    panBy: (delta) => {
        if (props.layout && props.layout.nodes.length > 0) {
            emit("panBy", delta);
        }
    },
    moveTo: (pos) => {
        if (props.layout && props.layout.nodes.length > 0) {
            emit("moveTo", pos);
        }
    },
    storageKey: "graph-overview-size",
    minSize: MINIMAP_MIN,
    maxSize: MINIMAP_MAX,
    defaultSize: MINIMAP_SIZE,
});

onMounted(() => {
    if (canvas.value) {
        const style = getComputedStyle(canvas.value);
        nodeColor = style.getPropertyValue("--node-color").trim() || nodeColor;
        viewColor = style.getPropertyValue("--view-color").trim() || viewColor;
        viewOutlineColor = style.getPropertyValue("--view-outline-color").trim() || viewOutlineColor;
    }
    recomputeTransform();
    redraw = true;
});

// ── Redraw triggers ──

watch(
    () => props.layout,
    () => {
        redraw = true;
    },
    { deep: true },
);
watch(
    () => props.viewportBoundingBox,
    () => {
        redraw = true;
    },
    { deep: true },
);
watch(
    () => props.selectedNodeId,
    () => {
        redraw = true;
    },
);
watch(minimapSize, () => {
    redraw = true;
});
watch(contentBounds, () => {
    recomputeTransform();
    redraw = true;
});

useAnimationFrame(() => {
    if (redraw && canvas.value) {
        renderMinimap();
        redraw = false;
    }
});

// ── Rendering ──

function renderMinimap() {
    const canvasTransform = getCanvasTransform();
    const ctx = canvas.value!.getContext("2d") as CanvasRenderingContext2D;
    ctx.resetTransform();
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    if (!props.layout) {
        return;
    }

    canvasTransform.applyToContext(ctx);

    // Draw nodes
    ctx.fillStyle = nodeColor;
    ctx.beginPath();
    for (const node of props.layout.nodes) {
        ctx.rect(node.x, node.y, node.width, node.height);
    }
    ctx.fill();

    // Draw selected node outline
    if (props.selectedNodeId) {
        const selected = props.layout.nodes.find((n) => n.id === props.selectedNodeId);
        if (selected) {
            const edge = 2 / canvasTransform.scaleX;
            ctx.beginPath();
            ctx.strokeStyle = nodeColor;
            ctx.lineWidth = edge;
            ctx.rect(selected.x - edge, selected.y - edge, selected.width + edge * 2, selected.height + edge * 2);
            ctx.stroke();
        }
    }

    // Draw viewport overlay
    ctx.beginPath();
    ctx.strokeStyle = viewOutlineColor;
    ctx.fillStyle = viewColor;
    ctx.lineWidth = 1 / canvasTransform.scaleX;
    ctx.rect(
        props.viewportBoundingBox.x,
        props.viewportBoundingBox.y,
        props.viewportBoundingBox.width,
        props.viewportBoundingBox.height,
    );
    ctx.fill();
    ctx.stroke();
}
</script>

<template>
    <div
        ref="minimap"
        class="graph-overview"
        :style="{ '--graph-overview-size': `${minimapSize + MINIMAP_PADDING + MINIMAP_BORDER}px` }">
        <canvas ref="canvas" class="graph-overview-body" :width="MINIMAP_MAX" :height="MINIMAP_MAX" />
    </div>
</template>

<style lang="scss" scoped>
@import "bootstrap/scss/_functions.scss";
@import "@/style/scss/theme/blue.scss";

.graph-overview {
    --graph-overview-size: 150px;

    border-top-left-radius: 0.3rem;
    cursor: nwse-resize;
    position: absolute;
    width: var(--graph-overview-size);
    height: var(--graph-overview-size);
    right: 0px;
    bottom: 0px;
    border-top: solid $border-color 1px;
    border-left: solid $border-color 1px;
    background: $white no-repeat url("@/assets/images/resizable.png");
    z-index: 2000;
    overflow: hidden;
    padding: 7px 0 0 7px;

    max-width: calc(300px + 7px + 1px);
    max-height: calc(300px + 7px + 1px);
    min-width: calc(50px + 7px + 1px);
    min-height: calc(50px + 7px + 1px);

    .graph-overview-body {
        cursor: pointer;
        position: relative;
        overflow: hidden;
        width: 100%;
        height: 100%;

        --node-color: #{$brand-primary};
        --view-color: #{fade-out($brand-dark, 0.8)};
        --view-outline-color: #{$brand-info};
    }
}
</style>
