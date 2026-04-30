import ELK, { type ElkExtendedEdge, type ElkNode } from "elkjs/lib/elk.bundled";
import { type Ref, ref, watch } from "vue";

import type { EdgeStyle, GraphEdge, GraphLayout, GraphNode } from "@/components/Graph/types";
import { computeControlPoints } from "@/utils/connectionPath";

import { type HistoryGraphResponse, mapEdges, mapNodes } from "./historyGraphMapper";

const elk = new ELK();

/**
 * Composable that takes API graph data and produces a positioned layout using ELK.js.
 *
 * Uses the history graph mapper to convert API types to generic graph types,
 * then runs ELK layered layout and extracts positioned nodes and edge paths.
 *
 * edgeStyle controls how edge points are computed:
 * - "orthogonal": uses ELK's routed sections (straight segments with bends)
 * - "curved": computes bezier control points between node ports (workflow editor style)
 */
export function useHistoryGraphLayout(
    graphData: Ref<HistoryGraphResponse | null>,
    edgeStyle: Ref<EdgeStyle> = ref("orthogonal") as Ref<EdgeStyle>,
) {
    const layout = ref<GraphLayout | null>(null);
    const layoutLoading = ref(false);

    watch(
        [graphData, edgeStyle],
        async ([data, style]) => {
            if (!data || data.nodes.length === 0) {
                layout.value = null;
                return;
            }

            layoutLoading.value = true;
            try {
                layout.value = await computeLayout(data, style);
            } catch (e) {
                console.error("History graph layout failed:", e);
                layout.value = null;
            } finally {
                layoutLoading.value = false;
            }
        },
        { immediate: true },
    );

    return { layout, layoutLoading };
}

async function computeLayout(data: HistoryGraphResponse, style: EdgeStyle): Promise<GraphLayout> {
    // Map API types to generic graph types via the history mapper
    const graphNodes = mapNodes(data.nodes, data.edges);
    const graphEdges = mapEdges(data.edges);

    // Build ELK graph
    const elkChildren: ElkNode[] = graphNodes.map((node) => ({
        id: node.id,
        width: node.width,
        height: node.height,
    }));

    const elkEdges: ElkExtendedEdge[] = graphEdges.map((edge) => ({
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
            "elk.edgeRouting": "ORTHOGONAL",
        },
        children: elkChildren,
        edges: elkEdges,
    };

    const result = await elk.layout(elkGraph);

    // Apply ELK positions to graph nodes
    const nodeById = new Map(graphNodes.map((n) => [n.id, n]));
    const layoutNodes: GraphNode[] = (result.children ?? []).map((elkNode) => {
        const gn = nodeById.get(elkNode.id)!;
        return {
            ...gn,
            x: elkNode.x ?? 0,
            y: elkNode.y ?? 0,
            width: elkNode.width ?? gn.width,
            height: elkNode.height ?? gn.height,
        };
    });

    // Build node position lookup for edge routing
    const nodePositions = new Map<string, { x: number; y: number; w: number; h: number }>();
    for (const n of layoutNodes) {
        nodePositions.set(n.id, { x: n.x, y: n.y, w: n.width, h: n.height });
    }

    let layoutEdges: GraphEdge[];

    if (style === "curved") {
        // Compute bezier control points between node ports (workflow editor style)
        layoutEdges = graphEdges.map((ge) => {
            const src = nodePositions.get(ge.source);
            const tgt = nodePositions.get(ge.target);
            let points: { x: number; y: number }[] = [];
            if (src && tgt) {
                const controlPoints = computeControlPoints(src.x + src.w, src.y + src.h / 2, tgt.x, tgt.y + tgt.h / 2);
                points = controlPoints.map(([x, y]) => ({ x, y }));
            }
            return { ...ge, points };
        });
    } else {
        // Extract edge paths from ELK's orthogonal routing sections
        const edgeById = new Map(graphEdges.map((e) => [e.id, e]));
        layoutEdges = (result.edges ?? []).map((elkEdge) => {
            const ge = edgeById.get(elkEdge.id)!;
            const points: { x: number; y: number }[] = [];

            const sections = (elkEdge as ElkExtendedEdge).sections ?? [];
            for (const section of sections) {
                points.push({ x: section.startPoint.x, y: section.startPoint.y });
                if (section.bendPoints) {
                    for (const bp of section.bendPoints) {
                        points.push({ x: bp.x, y: bp.y });
                    }
                }
                points.push({ x: section.endPoint.x, y: section.endPoint.y });
            }

            // Fallback: straight line between node edges
            if (points.length === 0) {
                const src = nodePositions.get(ge.source);
                const tgt = nodePositions.get(ge.target);
                if (src && tgt) {
                    points.push({ x: src.x + src.w, y: src.y + src.h / 2 });
                    points.push({ x: tgt.x, y: tgt.y + tgt.h / 2 });
                }
            }

            return { ...ge, points };
        });
    }

    return {
        nodes: layoutNodes,
        edges: layoutEdges,
        width: result.width ?? 0,
        height: result.height ?? 0,
    };
}
