<script setup lang="ts">
import { curveBasisPath, orthogonalPath } from "@/utils/connectionPath";

import type { EdgeStyle, GraphEdge } from "./types";

interface Props {
    edges: GraphEdge[];
    selectedNodeId?: string | null;
    width: number;
    height: number;
    edgeStyle?: EdgeStyle;
}

const props = withDefaults(defineProps<Props>(), {
    selectedNodeId: null,
    edgeStyle: "orthogonal",
});

/** Ribbon margin for collection edges — matches workflow editor's ribbonMargin */
const RIBBON_MARGIN = 4;
const RIBBON_OFFSETS = [-2 * RIBBON_MARGIN, -1 * RIBBON_MARGIN, 0, 1 * RIBBON_MARGIN, 2 * RIBBON_MARGIN];

function makePath(points: { x: number; y: number }[]): string {
    if (props.edgeStyle === "curved") {
        return curveBasisPath(points.map((p) => [p.x, p.y] as [number, number]));
    }
    return orthogonalPath(points);
}

/** For a single (non-collection) edge, return one path string */
function edgePaths(edge: GraphEdge): string[] {
    if (!edge.isCollection || edge.points.length < 2) {
        return [makePath(edge.points)];
    }
    // Collection ribbon: offset each path perpendicular to the edge direction.
    // For orthogonal/curved layouts the edges run mostly left-to-right,
    // so vertical offsets produce the ribbon effect.
    return RIBBON_OFFSETS.map((offset) => {
        const offsetPoints = edge.points.map((p) => ({ x: p.x, y: p.y + offset }));
        return makePath(offsetPoints);
    });
}

function edgeClass(edge: GraphEdge): Record<string, boolean> {
    const isConnected =
        !props.selectedNodeId || edge.source === props.selectedNodeId || edge.target === props.selectedNodeId;
    return {
        [edge.cssClass ?? "edge-default"]: true,
        "edge-dimmed": !isConnected,
        "edge-collection": !!edge.isCollection,
    };
}
</script>

<template>
    <svg class="graph-edges" :width="width" :height="height">
        <template v-for="edge in edges">
            <path
                v-for="(path, idx) in edgePaths(edge)"
                :key="`${edge.id}-${idx}`"
                :d="path"
                :class="edgeClass(edge)"
                fill="none" />
        </template>
    </svg>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.graph-edges {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
    overflow: visible;
    z-index: 0;
}

path {
    stroke-width: 2;
    stroke: $brand-primary;
    transition: opacity 0.2s ease;
}

.edge-dimmed {
    opacity: 0.3;
}
</style>
