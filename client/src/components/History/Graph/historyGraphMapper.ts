import { faBolt, faFile, faLayerGroup } from "@fortawesome/free-solid-svg-icons";

import type { components } from "@/api/schema";
import type { ConnectorVariant, GraphEdge, GraphNode } from "@/components/Graph/types";
import {
    stateFromJobSummary,
    stateFromPopulatedState,
    type StateRepresentation,
    STATES,
} from "@/components/History/Content/model/states";

type ApiGraphNode = components["schemas"]["GraphNode"];
type ApiGraphEdge = components["schemas"]["GraphEdge"];
export type HistoryGraphResponse = components["schemas"]["HistoryGraphResponse"];

/** Domain payload that the mapper attaches to every `GraphNode.data`.
 *  Extends `Record<string, unknown>` so a typed `HistoryGraphNode` remains
 *  assignable to the generic `GraphNode` consumed by the renderer. */
export interface HistoryGraphNodeData extends Record<string, unknown> {
    src: ApiGraphNode["src"];
    typeLabel: string;
    /** Encoded id of the underlying item (no prefix). */
    itemId: string;
    toolId: string | null | undefined;
    executionIndex: number | undefined;
    inputCount: number;
    outputCount: number;
    state: string | null | undefined;
    stateText: string | null;
    stateDisplayName: string | null;
    stateSpin: boolean;
}

export type HistoryGraphNode = GraphNode<HistoryGraphNodeData>;

/** Fixed node width — uniform across all node types. */
const NODE_WIDTH = 200;

/** User-facing labels keyed by node src */
export const NODE_TYPE_LABELS: Record<string, string> = {
    hda: "Dataset",
    hdca: "Collection",
    tool_request: "Tool Execution",
};

const NODE_ICONS: Record<string, typeof faFile> = {
    hda: faFile,
    hdca: faLayerGroup,
    tool_request: faBolt,
};

const NODE_CSS_CLASS: Record<string, string> = {
    hda: "node-dataset",
    hdca: "node-collection",
    tool_request: "node-tool-request",
};

/** Stable string key for the generic renderer, derived from the (src, id) ref. */
export function nodeKey(ref: { src: string; id: string }): string {
    return `${ref.src}:${ref.id}`;
}

// ── Label resolution ──

function resolveNodeLabel(node: ApiGraphNode, executionIndex?: number): string {
    const hid = node.hid ? `${node.hid}: ` : "";
    switch (node.src) {
        case "hda":
            return `${hid}${node.name ?? node.extension ?? "Dataset"}`;
        case "hdca":
            return `${hid}${node.name ?? node.collection_type ?? "Collection"}`;
        case "tool_request": {
            const idx = executionIndex !== undefined ? `${executionIndex}: ` : "";
            return `${idx}${node.tool_name ?? shortenToolId(node.tool_id)}`;
        }
    }
}

function resolveNodeBadge(node: ApiGraphNode): string | null {
    switch (node.src) {
        case "hda":
            return node.extension ?? null;
        case "hdca":
            return node.collection_type ?? null;
        case "tool_request":
            return null;
    }
}

function shortenToolId(toolId: string | null | undefined): string {
    if (!toolId) {
        return "Tool";
    }
    // "toolshed.g2.bx.psu.edu/repos/iuc/bwa_mem/bwa_mem/1.0" → "bwa_mem"
    const parts = toolId.split("/");
    if (parts.length >= 2) {
        return parts[parts.length - 2] ?? toolId;
    }
    return toolId;
}

function isCollectionEdge(edge: ApiGraphEdge): boolean {
    return edge.type === "collection_input" || edge.type === "collection_output";
}

/**
 * Connector variant at one end of an edge — the single source of truth shared by
 * the edge ribbon and the node connectors, so the two can never disagree.
 */
function edgeEndVariant(ref: { src: string }, edge: ApiGraphEdge): ConnectorVariant {
    if (ref.src === "hdca") {
        return "multiple";
    }
    if (ref.src === "hda") {
        return "single";
    }
    return isCollectionEdge(edge) ? "multiple" : "single";
}

/** Merged connector variant for a node side — "multiple" if any edge there is a collection. */
function mergedConnectorVariant(variants: ConnectorVariant[]): ConnectorVariant | null {
    if (variants.length === 0) {
        return null;
    }
    return variants.some((variant) => variant === "multiple") ? "multiple" : "single";
}

/** Display state for a node, per src type. */
function resolveDisplayState(node: ApiGraphNode): string | null {
    switch (node.src) {
        case "hda":
            return node.state ?? null;
        case "hdca":
            // node.state carries populated_state for collections.
            return (
                stateFromPopulatedState(node.state) ?? stateFromJobSummary(node.job_state_summary) ?? node.state ?? null
            );
        case "tool_request":
            return null;
    }
}

/** Connection summary shown in a tool node's body, e.g. "3 inputs, 2 outputs". */
function toolConnectionSummary(inputCount: number, outputCount: number): string {
    const parts: string[] = [];
    if (inputCount > 0) {
        parts.push(`${inputCount} input${inputCount === 1 ? "" : "s"}`);
    }
    if (outputCount > 0) {
        parts.push(`${outputCount} output${outputCount === 1 ? "" : "s"}`);
    }
    return parts.join(", ");
}

// ── Public API ──

/**
 * Map API graph nodes to generic GraphNode[] for the renderer.
 *
 * Nodes are emitted collapsed, with a fixed width and no position or height —
 * GraphView measures each node's rendered height, then positions everything
 * with ELK.
 */
export function mapNodes(apiNodes: ApiGraphNode[], apiEdges: ApiGraphEdge[]): HistoryGraphNode[] {
    // Per node, the connector variant of each incoming / outgoing edge end —
    // used to derive the merged connector variant and the connection counts.
    const inputVariants = new Map<string, ConnectorVariant[]>();
    const outputVariants = new Map<string, ConnectorVariant[]>();
    for (const edge of apiEdges) {
        const sourceKey = nodeKey(edge.source);
        const targetKey = nodeKey(edge.target);
        if (!inputVariants.has(targetKey)) {
            inputVariants.set(targetKey, []);
        }
        inputVariants.get(targetKey)!.push(edgeEndVariant(edge.target, edge));
        if (!outputVariants.has(sourceKey)) {
            outputVariants.set(sourceKey, []);
        }
        outputVariants.get(sourceKey)!.push(edgeEndVariant(edge.source, edge));
    }

    // Position-based execution index for tool_request nodes. The graph response
    // is sorted by db_id (creation order), so the n-th tool_request here is
    // the n-th execution in the response — stable when the graph covers the
    // whole history, drifts when truncated or seed-filtered.
    const executionIndices = new Map<string, number>();
    let execCounter = 0;
    for (const node of apiNodes) {
        if (node.src === "tool_request") {
            execCounter += 1;
            executionIndices.set(node.id, execCounter);
        }
    }

    return apiNodes.map((node) => {
        const key = nodeKey(node);
        const isToolRequest = node.src === "tool_request";
        const executionIndex = isToolRequest ? executionIndices.get(node.id) : undefined;
        const inputs = inputVariants.get(key) ?? [];
        const outputs = outputVariants.get(key) ?? [];

        const rawState = resolveDisplayState(node);
        const displayState = rawState === "failed" ? "error" : rawState;
        const stateKey = displayState as keyof typeof STATES | undefined;
        const stateRep: StateRepresentation | null = stateKey && stateKey in STATES ? STATES[stateKey] : null;

        // Tool nodes summarise their connections; data nodes show their state text.
        const bodyText = isToolRequest
            ? toolConnectionSummary(inputs.length, outputs.length)
            : (stateRep?.text ?? null);

        return {
            id: key,
            x: 0,
            y: 0,
            width: NODE_WIDTH,
            height: 0,
            label: resolveNodeLabel(node, executionIndex),
            icon: stateRep?.icon ?? NODE_ICONS[node.src] ?? faFile,
            badge: resolveNodeBadge(node),
            cssClass: NODE_CSS_CLASS[node.src],
            inputConnector: mergedConnectorVariant(inputs),
            outputConnector: mergedConnectorVariant(outputs),
            data: {
                src: node.src,
                typeLabel: NODE_TYPE_LABELS[node.src] ?? node.src,
                /** Encoded id of the underlying item (no prefix). */
                itemId: node.id,
                toolId: isToolRequest ? node.tool_id : null,
                executionIndex,
                inputCount: inputs.length,
                outputCount: outputs.length,
                state: displayState,
                stateText: bodyText,
                stateDisplayName: stateRep?.displayName ?? null,
                stateSpin: stateRep?.spin ?? false,
            },
        };
    });
}

/**
 * Map API graph edges to generic GraphEdge[]. Points are empty — GraphView's
 * layout fills them in after positioning.
 */
export function mapEdges(apiEdges: ApiGraphEdge[]): GraphEdge[] {
    return apiEdges.map((edge, idx) => ({
        id: `e${idx}`,
        source: nodeKey(edge.source),
        target: nodeKey(edge.target),
        cssClass: isCollectionEdge(edge) ? "edge-collection" : "edge-dataset",
        sourceVariant: edgeEndVariant(edge.source, edge),
        targetVariant: edgeEndVariant(edge.target, edge),
        points: [],
    }));
}
