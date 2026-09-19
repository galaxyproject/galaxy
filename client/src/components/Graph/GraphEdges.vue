<script setup lang="ts">
import { curveBasisPath } from "@/utils/connectionPath";

import type { GraphEdge } from "./types";

interface Props {
    edges: GraphEdge[];
    /** Lineage of the selected node. Edges where either endpoint isn't in this
     *  set are dimmed. Null means no filtering (nothing dimmed). */
    focusedNodeIds?: Set<string> | null;
    width: number;
    height: number;
}

const props = withDefaults(defineProps<Props>(), {
    focusedNodeIds: null,
});

/** Ribbon margin for collection edges — the gap between parallel ribbon strands. */
const RIBBON_MARGIN = 4;
const RIBBON_OFFSETS = [-2 * RIBBON_MARGIN, -1 * RIBBON_MARGIN, 0, 1 * RIBBON_MARGIN, 2 * RIBBON_MARGIN];

function makePath(points: { x: number; y: number }[]): string {
    return curveBasisPath(points.map((p) => [p.x, p.y] as [number, number]));
}

/**
 * Return the SVG path(s) for an edge. A single line when both ends are "single";
 * otherwise a ribbon whose offsets spread at a "multiple" end and converge to 0
 * at a "single" end — so a dataset→collection edge morphs from one line to a ribbon.
 */
function edgePaths(edge: GraphEdge): string[] {
    const startMultiple = edge.sourceVariant === "multiple";
    const endMultiple = edge.targetVariant === "multiple";
    if ((!startMultiple && !endMultiple) || edge.points.length < 2) {
        return [makePath(edge.points)];
    }
    // Start-side control points take the source offset, end-side points the
    // target offset; the bezier smooths the morph between them.
    const mid = Math.floor(edge.points.length / 2);
    return RIBBON_OFFSETS.map((offset) => {
        const startOffset = startMultiple ? offset : 0;
        const endOffset = endMultiple ? offset : 0;
        const offsetPoints = edge.points.map((p, i) => ({
            x: p.x,
            y: p.y + (i < mid ? startOffset : endOffset),
        }));
        return makePath(offsetPoints);
    });
}

function edgeClass(edge: GraphEdge): Record<string, boolean> {
    const inFocus =
        !props.focusedNodeIds || (props.focusedNodeIds.has(edge.source) && props.focusedNodeIds.has(edge.target));
    return {
        [edge.cssClass ?? "edge-default"]: true,
        "edge-dimmed": !inFocus,
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
