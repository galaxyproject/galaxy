<script setup lang="ts">
import { useElementBounding } from "@vueuse/core";
import { computed, nextTick, type Ref, ref, watch } from "vue";

import { useD3Zoom } from "@/composables/d3Zoom";
import { useViewportBoundingBox } from "@/composables/viewportBoundingBox";
import { maxZoom, minZoom } from "@/utils/zoomLevels";

import type { EdgeStyle, GraphLayout, GraphNode } from "./types";

import GraphEdges from "./GraphEdges.vue";
import GraphNodeComponent from "./GraphNode.vue";
import ZoomControl from "./ZoomControl.vue";

interface Props {
    layout: GraphLayout | null;
    focusNodeId?: string | null;
    edgeStyle?: EdgeStyle;
    showZoomControls?: boolean;
    showMinimap?: boolean;
    /** Minimap component — injected by consumer to avoid domain coupling */
    minimapComponent?: object | null;
}

const props = withDefaults(defineProps<Props>(), {
    focusNodeId: null,
    edgeStyle: "orthogonal",
    showZoomControls: true,
    showMinimap: true,
    minimapComponent: null,
});

const emit = defineEmits<{ (e: "nodeSelected", node: GraphNode | null): void }>();

const selectedNodeId = ref<string | null>(null);

// Separate ref for the zoom level displayed in ZoomControl.
// Set explicitly to snapped values — avoids floating point drift from d3.
const scale = ref(1);

// d3 zoom is attached to the inner canvas-container, NOT the outer wrapper.
// This keeps ZoomControl and minimap outside the d3 event target.
const canvasContainer: Ref<HTMLElement | null> = ref(null);
const { transform, setZoom, panBy, moveTo } = useD3Zoom(1, minZoom, maxZoom, canvasContainer, { x: 50, y: 50 });

// Element bounding for viewport computation (needed by minimap)
const elementBounding = useElementBounding(canvasContainer, { windowResize: false, windowScroll: false });

// Viewport bounding box in content coordinates
const { viewportBoundingBox } = useViewportBoundingBox(elementBounding, scale, transform);

// Sync scale ref from d3 zoom events (for scroll-wheel zoom)
watch(
    () => transform.value.k,
    (k) => {
        scale.value = k;
    },
);

function onZoom(zoomLevel: number) {
    setZoom(zoomLevel);
}

const canvasStyle = computed(() => ({
    transform: `translate(${transform.value.x}px, ${transform.value.y}px) scale(${transform.value.k})`,
}));

function onNodeSelect(nodeId: string) {
    if (selectedNodeId.value === nodeId) {
        selectedNodeId.value = null;
        emit("nodeSelected", null);
    } else {
        selectedNodeId.value = nodeId;
        const node = props.layout?.nodes.find((n) => n.id === nodeId) ?? null;
        emit("nodeSelected", node);
    }
}

// Canvas background click deselects
const mouseMovementThreshold = 9;
let pointerDownPos: { x: number; y: number } | null = null;

function onPointerDown(e: PointerEvent) {
    pointerDownPos = { x: e.clientX, y: e.clientY };
}

function onPointerUp(e: PointerEvent) {
    if (!pointerDownPos) {
        return;
    }
    const dx = Math.abs(e.clientX - pointerDownPos.x);
    const dy = Math.abs(e.clientY - pointerDownPos.y);
    pointerDownPos = null;
    const clickedOnNode = !!(e.target as HTMLElement).closest(".graph-node");
    if (dx + dy <= mouseMovementThreshold && !clickedOnNode) {
        selectedNodeId.value = null;
        emit("nodeSelected", null);
    }
}

// Center on focus node or bounding box after layout
watch(
    () => props.layout,
    async (newLayout) => {
        if (!newLayout) {
            return;
        }
        await nextTick();

        if (props.focusNodeId) {
            const focusNode = newLayout.nodes.find((n) => n.id === props.focusNodeId);
            if (focusNode) {
                moveTo({ x: focusNode.x + focusNode.width / 2, y: focusNode.y + focusNode.height / 2 });
                return;
            }
        }

        if (newLayout.nodes.length > 0) {
            moveTo({ x: newLayout.width / 2, y: newLayout.height / 2 });
        }
    },
);
</script>

<template>
    <div class="graph-canvas rounded">
        <ZoomControl v-if="showZoomControls" :zoom-level="scale" @onZoom="onZoom" />
        <div ref="canvasContainer" class="canvas-container" @pointerdown="onPointerDown" @pointerup="onPointerUp">
            <div v-if="layout" class="graph-node-area" :style="canvasStyle">
                <GraphEdges
                    :edges="layout.edges"
                    :selected-node-id="selectedNodeId"
                    :width="layout.width + 200"
                    :height="layout.height + 200"
                    :edge-style="edgeStyle" />
                <GraphNodeComponent
                    v-for="node in layout.nodes"
                    :key="node.id"
                    :node="node"
                    :selected="node.id === selectedNodeId"
                    @select="onNodeSelect" />
            </div>
        </div>
        <component
            :is="minimapComponent"
            v-if="showMinimap && minimapComponent && layout"
            :layout="layout"
            :viewport-bounding-box="viewportBoundingBox"
            :selected-node-id="selectedNodeId"
            :parent-right="elementBounding.right.value"
            :parent-bottom="elementBounding.bottom.value"
            @panBy="panBy"
            @moveTo="moveTo" />
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.graph-canvas {
    flex: 1;
    width: 100%;
    position: relative;
    overflow: hidden;
}

.canvas-container {
    width: 100%;
    height: 100%;
    overflow: hidden;
    position: relative;
    background: $white;
}

.graph-node-area {
    position: absolute;
    top: 0;
    left: 0;
    transform-origin: 0 0;
}
</style>
