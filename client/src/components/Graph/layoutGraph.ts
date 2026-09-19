import ELK, { type ElkExtendedEdge, type ElkNode } from "elkjs/lib/elk.bundled";

import { computeControlPoints } from "@/utils/connectionPath";

import type { GraphEdge, GraphLayout, GraphNode } from "./types";

const elk = new ELK();

/**
 * Position a graph with ELK (layered, left-to-right) and route its edges as
 * bezier curves between node centres.
 *
 * Input nodes must already carry their measured `width`/`height`; this assigns
 * each node an `x`/`y` and each edge its `points`. Generic and domain-free.
 */
export async function layoutGraph(nodes: GraphNode[], edges: GraphEdge[]): Promise<GraphLayout> {
    const elkChildren: ElkNode[] = nodes.map((node) => ({
        id: node.id,
        width: node.width,
        height: node.height,
    }));
    const elkEdges: ElkExtendedEdge[] = edges.map((edge) => ({
        id: edge.id,
        sources: [edge.source],
        targets: [edge.target],
    }));

    const elkGraph: ElkNode = {
        id: "root",
        layoutOptions: {
            "elk.algorithm": "layered",
            "elk.direction": "RIGHT",
            "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
            "elk.layered.spacing.baseValue": "80",
            "elk.spacing.nodeNode": "40",
            "elk.layered.spacing.nodeNodeBetweenLayers": "80",
        },
        children: elkChildren,
        edges: elkEdges,
    };

    const result = await elk.layout(elkGraph);

    const placedById = new Map((result.children ?? []).map((child) => [child.id, child]));
    const layoutNodes: GraphNode[] = nodes.map((node) => {
        const placed = placedById.get(node.id);
        return { ...node, x: placed?.x ?? 0, y: placed?.y ?? 0 };
    });

    // Route each edge between the source node's right edge and the target
    // node's left edge, both at the node's vertical centre.
    const nodeById = new Map(layoutNodes.map((node) => [node.id, node]));
    const layoutEdges: GraphEdge[] = edges.map((edge) => {
        const source = nodeById.get(edge.source);
        const target = nodeById.get(edge.target);
        let points: { x: number; y: number }[] = [];
        if (source && target) {
            // Anchor at the node's merged connector (its first body row), or the
            // node's vertical centre when it has no body.
            const startX = source.x + source.width;
            const startY = source.y + (source.connectorY ?? source.height / 2);
            const endX = target.x;
            const endY = target.y + (target.connectorY ?? target.height / 2);
            points = computeControlPoints(startX, startY, endX, endY).map(([x, y]) => ({ x, y }));
        }
        return { ...edge, points };
    });

    return {
        nodes: layoutNodes,
        edges: layoutEdges,
        width: result.width ?? 0,
        height: result.height ?? 0,
    };
}
