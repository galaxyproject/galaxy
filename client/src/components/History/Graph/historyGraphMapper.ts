import { faFile, faLayerGroup, faWrench } from "@fortawesome/free-solid-svg-icons";

import type { components } from "@/api/schema";
import type { GraphEdge, GraphNode, GraphNodePort } from "@/components/Graph/types";
import { type StateRepresentation, STATES } from "@/components/History/Content/model/states";

type ApiGraphNode = components["schemas"]["GraphNode"];
type ApiGraphEdge = components["schemas"]["GraphEdge"];
export type HistoryGraphResponse = components["schemas"]["HistoryGraphResponse"];

/** Node width — uniform across all types */
const NODE_WIDTH = 200;

/** Compute node height based on content: header + ports + padding */
const HEADER_LINE_HEIGHT = 20;
const HEADER_PADDING = 10;
const HEADER_ICON_CHARS = 3;
const CHARS_PER_LINE = 22;
const PORT_ROW_HEIGHT = 18;
const RULE_HEIGHT = 5;
const BODY_PADDING = 8;
const MIN_NODE_HEIGHT = 32;

function estimateHeaderLines(label: string): number {
    const effectiveLength = label.length + HEADER_ICON_CHARS;
    return Math.max(1, Math.ceil(effectiveLength / CHARS_PER_LINE));
}

function computeNodeHeight(
    label: string,
    inputCount: number,
    outputCount: number,
    hasBadgeBody: boolean = false,
): number {
    const headerLines = estimateHeaderLines(label);
    const headerHeight = headerLines * HEADER_LINE_HEIGHT + HEADER_PADDING;
    if (inputCount === 0 && outputCount === 0 && !hasBadgeBody) {
        return Math.max(MIN_NODE_HEIGHT, headerHeight);
    }
    const portRows = inputCount + outputCount;
    const rule = inputCount > 0 && outputCount > 0 ? RULE_HEIGHT : 0;
    const badgeRow = hasBadgeBody ? PORT_ROW_HEIGHT + BODY_PADDING : 0;
    return headerHeight + portRows * PORT_ROW_HEIGHT + rule + BODY_PADDING + badgeRow;
}

/** User-facing type labels */
export const NODE_TYPE_LABELS: Record<string, string> = {
    dataset: "Dataset",
    collection: "Collection",
    tool_request: "Tool Execution",
};

const NODE_ICONS: Record<string, typeof faFile> = {
    dataset: faFile,
    collection: faLayerGroup,
    tool_request: faWrench,
};

const NODE_CSS_CLASS: Record<string, string> = {
    dataset: "node-dataset",
    collection: "node-collection",
    tool_request: "node-tool-request",
};

// ── Label resolution ──

function resolveNodeLabel(node: ApiGraphNode): string {
    const hid = node.hid ? `${node.hid}: ` : "";
    switch (node.type) {
        case "dataset":
            return `${hid}${node.name ?? node.extension ?? "Dataset"}`;
        case "collection":
            return `${hid}${node.name ?? node.collection_type ?? "Collection"}`;
        case "tool_request":
            return node.tool_name ?? shortenToolId(node.tool_id);
    }
}

function resolveNodeBadge(node: ApiGraphNode): string | null {
    switch (node.type) {
        case "dataset":
            return node.extension ?? null;
        case "collection":
            return node.collection_type ?? null;
        case "tool_request":
            return null;
    }
}

function shortenToolId(toolId: string | null | undefined): string {
    if (!toolId) {
        return "Tool";
    }
    // Strip toolshed prefix:
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

// ── Public API ──

/**
 * Map API graph nodes to generic GraphNode[] for the renderer.
 * Returns nodes with dimensions, labels, icons, badges, and domain data.
 */
export function mapNodes(apiNodes: ApiGraphNode[], apiEdges: ApiGraphEdge[]): GraphNode[] {
    // Build a lookup for node labels by ID
    const nodeLabels = new Map<string, string>();
    for (const node of apiNodes) {
        nodeLabels.set(node.id, resolveNodeLabel(node));
    }

    // Build input/output port lists per node from edges
    const inputPorts = new Map<string, GraphNodePort[]>();
    const outputPorts = new Map<string, GraphNodePort[]>();
    for (const edge of apiEdges) {
        const sourceLabel = nodeLabels.get(edge.source) ?? edge.source;
        const targetLabel = nodeLabels.get(edge.target) ?? edge.target;

        // Target node gets an input port labeled by the source
        if (!inputPorts.has(edge.target)) {
            inputPorts.set(edge.target, []);
        }
        inputPorts.get(edge.target)!.push({ name: edge.source, label: sourceLabel });

        // Source node gets an output port labeled by the target
        if (!outputPorts.has(edge.source)) {
            outputPorts.set(edge.source, []);
        }
        outputPorts.get(edge.source)!.push({ name: edge.target, label: targetLabel });
    }

    return apiNodes.map((node) => {
        // Only tool_request nodes show input/output port lists.
        // Dataset and collection nodes show state + badge in the body.
        const isToolRequest = node.type === "tool_request";
        const inputs = isToolRequest ? (inputPorts.get(node.id) ?? []) : [];
        const outputs = isToolRequest ? (outputPorts.get(node.id) ?? []) : [];
        const inputCount = inputPorts.get(node.id)?.length ?? 0;
        const outputCount = outputPorts.get(node.id)?.length ?? 0;
        const badge = resolveNodeBadge(node);

        // For datasets/collections, use state to determine icon.
        // State-based coloring is handled by data-state attribute on the node element,
        // which triggers the global $galaxy-state-bg / $galaxy-state-border rules from base.scss.
        // Collections return populated_state ("ok"/"new"/"failed") — map "failed" → "error"
        // to align with the dataset state vocabulary used by the STATES map and CSS rules.
        const rawState = node.state;
        const displayState = rawState === "failed" ? "error" : rawState;
        const stateKey = displayState as keyof typeof STATES | undefined;
        const stateRep: StateRepresentation | null =
            !isToolRequest && stateKey && stateKey in STATES ? STATES[stateKey] : null;
        const icon = stateRep?.icon ?? NODE_ICONS[node.type] ?? faFile;
        const cssClass = NODE_CSS_CLASS[node.type];

        // Data nodes always have a body (badge + state text)
        const hasBody = !isToolRequest;
        const label = nodeLabels.get(node.id)!;
        return {
            id: node.id,
            x: 0,
            y: 0,
            width: NODE_WIDTH,
            height: computeNodeHeight(label, inputs.length, outputs.length, hasBody),
            label,
            icon,
            badge,
            cssClass,
            inputs,
            outputs,
            data: {
                type: node.type,
                typeLabel: NODE_TYPE_LABELS[node.type] ?? node.type,
                /** Encoded ID without the type prefix (d/c/r) */
                encodedId: node.id.slice(1),
                toolId: isToolRequest ? node.tool_id : null,
                inputCount,
                outputCount,
                state: displayState,
                stateText: stateRep?.text ?? null,
                stateDisplayName: stateRep?.displayName ?? null,
                stateSpin: stateRep?.spin ?? false,
            },
        };
    });
}

/**
 * Map API graph edges to generic GraphEdge[] for the renderer.
 * Points are set to empty — the layout composable fills them in.
 */
export function mapEdges(apiEdges: ApiGraphEdge[]): GraphEdge[] {
    return apiEdges.map((edge, idx) => ({
        id: `e${idx}`,
        source: edge.source,
        target: edge.target,
        cssClass: isCollectionEdge(edge) ? "edge-collection" : "edge-dataset",
        isCollection: isCollectionEdge(edge),
        points: [],
    }));
}
