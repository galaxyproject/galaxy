<script setup lang="ts">
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useElementBounding } from "@vueuse/core";
import { computed, nextTick, type Ref, ref, watch } from "vue";

import { useD3Zoom } from "@/composables/d3Zoom";
import { useViewportBoundingBox } from "@/composables/viewportBoundingBox";
import { maxZoom, minZoom } from "@/utils/zoomLevels";

import { useFocusedNodes } from "./composables/useFocusedNodes";
import { layoutGraph } from "./layoutGraph";
import type { GraphEdge, GraphLayout, GraphNode } from "./types";

import GraphEdges from "./GraphEdges.vue";
import GraphMinimap from "./GraphMinimap.vue";
import GraphNodeComponent from "./GraphNode.vue";
import ZoomControl from "./ZoomControl.vue";

// `GraphNode<any>` here — the view doesn't know (or care) about the domain
// payload on `data`; callers parameterise that on their side. Vue 2.7 doesn't
// support `<script setup generic>` so we widen explicitly.
type AnyGraphNode = GraphNode<any>;

interface Props {
    /** Graph structure — each node carries its content and a fixed width; the
     *  view measures the rendered height, then positions everything with ELK. */
    nodes: AnyGraphNode[];
    edges: GraphEdge[];
    focusNodeId?: string | null;
    showZoomControls?: boolean;
    showMinimap?: boolean;
    nodeColor?: (node: AnyGraphNode) => string | null | undefined;
    centerOnSelect?: boolean;
    showScrollOverlays?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    focusNodeId: null,
    showZoomControls: true,
    showMinimap: true,
    nodeColor: undefined,
    centerOnSelect: false,
    showScrollOverlays: false,
});

const emit = defineEmits<{ (e: "nodeSelected", node: AnyGraphNode | null): void }>();

interface NodeSize {
    width: number;
    height: number;
    /** Merged connector Y offset (px from node top) — the first body row's centre. */
    connectorY?: number;
}

// ── Measure-then-layout ──────────────────────────────────────────────
// Nodes render first so the browser computes their wrapped height; once every
// node has reported a size, ELK positions them. The current layout stays on
// screen while a re-layout runs, so a data refresh never blanks the view.
const measuredSizes = ref(new Map<string, NodeSize>());
const layout = ref<GraphLayout | null>(null);
const measuring = computed(() => layout.value === null && props.nodes.length > 0);

function onNodeResize(id: string, size: NodeSize) {
    const next = new Map(measuredSizes.value);
    next.set(id, size);
    measuredSizes.value = next;
}

// Coalesce the measurement burst into a single layout run. A macrotask delay
// lets ResizeObserver deliver this frame's sizes before the layout runs.
let layoutScheduled: ReturnType<typeof setTimeout> | null = null;
function scheduleLayout() {
    if (layoutScheduled !== null) {
        return;
    }
    layoutScheduled = setTimeout(() => {
        layoutScheduled = null;
        void runLayout();
    }, 0);
}

let layoutToken = 0;
let fitted = false;
async function runLayout() {
    const token = ++layoutToken;
    const sized = props.nodes.map((node) => {
        const measured = measuredSizes.value.get(node.id);
        return {
            ...node,
            height: measured?.height ?? node.height,
            connectorY: measured?.connectorY,
        };
    });
    const result = await layoutGraph(sized, props.edges);
    if (token !== layoutToken) {
        return; // superseded by a newer run
    }
    layout.value = result;
    await nextTick();
    if (!fitted) {
        fitted = true;
        fitView();
    }
}

// Run layout once every current node has reported a measured size.
watch(
    [measuredSizes, () => props.nodes],
    () => {
        if (props.nodes.length > 0 && props.nodes.every((node) => measuredSizes.value.has(node.id))) {
            scheduleLayout();
        }
    },
    { immediate: true },
);

// ── Zoom / pan ───────────────────────────────────────────────────────
const scale = ref(1);
const canvasContainer: Ref<HTMLElement | null> = ref(null);
const { transform, setZoom, panBy, moveTo } = useD3Zoom(1, minZoom, maxZoom, canvasContainer, { x: 50, y: 50 });
const elementBounding = useElementBounding(canvasContainer, { windowResize: false, windowScroll: false });
const { viewportBoundingBox } = useViewportBoundingBox(elementBounding, scale, transform);

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

// ── Fit to view (initial layout only) ────────────────────────────────
function fitView() {
    const current = layout.value;
    if (!current || current.nodes.length === 0) {
        return;
    }
    const focusNode = props.focusNodeId ? current.nodes.find((node) => node.id === props.focusNodeId) : null;
    if (focusNode) {
        moveTo({ x: focusNode.x + focusNode.width / 2, y: focusNode.y + focusNode.height / 2 });
        return;
    }
    const viewWidth = elementBounding.width.value;
    const viewHeight = elementBounding.height.value;
    if (viewWidth > 0 && viewHeight > 0 && current.width > 0 && current.height > 0) {
        const padding = 40;
        const fit = Math.min((viewWidth - padding) / current.width, (viewHeight - padding) / current.height);
        setZoom(Math.max(minZoom, Math.min(1, fit)));
    }
    moveTo({ x: current.width / 2, y: current.height / 2 });
}

// ── Selection ────────────────────────────────────────────────────────
const selectedNodeId = ref<string | null>(null);

// Lineage of the selected node — drives the dimming of out-of-focus nodes/edges.
const { focusedNodeIds } = useFocusedNodes(selectedNodeId, {
    upstream: (id) => props.edges.filter((e) => e.target === id).map((e) => e.source),
    downstream: (id) => props.edges.filter((e) => e.source === id).map((e) => e.target),
});

function onNodeSelect(nodeId: string) {
    if (selectedNodeId.value === nodeId) {
        selectedNodeId.value = null;
        emit("nodeSelected", null);
        return;
    }
    selectedNodeId.value = nodeId;
    const node = layout.value?.nodes.find((candidate) => candidate.id === nodeId) ?? null;
    emit("nodeSelected", node);
    if (props.centerOnSelect && node) {
        moveTo({ x: node.x + node.width / 2, y: node.y + node.height / 2 });
    }
}

const mouseMovementThreshold = 9;
let pointerDownPos: { x: number; y: number } | null = null;

function onPointerDown(e: PointerEvent) {
    pointerDownPos = { x: e.clientX, y: e.clientY };
}

function onPointerUp(e: PointerEvent) {
    if (!pointerDownPos) {
        return;
    }
    const moved = Math.abs(e.clientX - pointerDownPos.x) + Math.abs(e.clientY - pointerDownPos.y);
    pointerDownPos = null;
    if (moved <= mouseMovementThreshold && !(e.target as HTMLElement).closest(".graph-node")) {
        selectedNodeId.value = null;
        emit("nodeSelected", null);
    }
}

// Render current node content at the latest known positions. Keeping the prior
// positions during a re-layout (rather than clearing them) avoids a blank.
const renderNodes = computed<GraphNode[]>(() => {
    const positioned = layout.value;
    if (!positioned) {
        return props.nodes;
    }
    const placedById = new Map(positioned.nodes.map((node) => [node.id, node]));
    return props.nodes.map((node) => {
        const placed = placedById.get(node.id);
        return placed ? { ...node, x: placed.x, y: placed.y } : node;
    });
});
</script>

<template>
    <div class="graph-canvas rounded">
        <ZoomControl v-if="showZoomControls && layout" :zoom-level="scale" @onZoom="onZoom" />
        <div ref="canvasContainer" class="canvas-container" @pointerdown="onPointerDown" @pointerup="onPointerUp">
            <div class="graph-node-area" :class="{ measuring }" :style="canvasStyle">
                <GraphEdges
                    v-if="layout"
                    :edges="layout.edges"
                    :focused-node-ids="focusedNodeIds"
                    :width="layout.width + 200"
                    :height="layout.height + 200" />
                <GraphNodeComponent
                    v-for="node in renderNodes"
                    :key="node.id"
                    :node="node"
                    :selected="node.id === selectedNodeId"
                    :out-of-focus="focusedNodeIds !== null && !focusedNodeIds.has(node.id)"
                    @select="onNodeSelect"
                    @resize="onNodeResize" />
            </div>
            <div v-if="measuring" class="graph-loading">
                <FontAwesomeIcon :icon="faSpinner" spin size="2x" />
            </div>
        </div>
        <div v-if="showScrollOverlays" class="graph-scroll-overlay overlay-left" />
        <div v-if="showScrollOverlays" class="graph-scroll-overlay overlay-right" />
        <GraphMinimap
            v-if="showMinimap && layout"
            :layout="layout"
            :viewport-bounding-box="viewportBoundingBox"
            :selected-node-id="selectedNodeId"
            :node-color="nodeColor"
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

    // While measuring the initial layout, nodes are rendered (so they can be
    // sized) but hidden until they are positioned.
    &.measuring {
        visibility: hidden;
    }
}

.graph-loading {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: $text-muted;
}

.graph-scroll-overlay {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1.5rem;
    background: $gray-200;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease;
    z-index: 1;

    &.overlay-left {
        left: 0;
    }

    &.overlay-right {
        right: 0;
    }
}

.graph-canvas:hover .graph-scroll-overlay {
    opacity: 0.5;
    pointer-events: auto;
}
</style>
