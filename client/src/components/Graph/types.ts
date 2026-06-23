import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";

/** Connector visual variant — "multiple" renders larger (used to mark collections). */
export type ConnectorVariant = "single" | "multiple";

/** A positioned node after layout. `TData` is the domain payload the mapper
 *  attaches — callers parameterise it (e.g. `GraphNode<HistoryGraphNodeData>`)
 *  for typed access; the default leaves it open for non-typed consumers. */
export interface GraphNode<TData = Record<string, unknown>> {
    id: string;
    x: number;
    y: number;
    width: number;
    height: number;
    label: string;
    icon: IconDefinition;
    badge?: string | null;
    cssClass?: string;
    /** Connector straddling the node's input (left) edge when it has incoming edges. */
    inputConnector?: ConnectorVariant | null;
    /** Connector straddling the node's output (right) edge when it has outgoing edges. */
    outputConnector?: ConnectorVariant | null;
    /** Measured Y offset (px from node top) of the merged connectors. */
    connectorY?: number;
    /** Domain data attached by the mapper */
    data?: TData;
}

/** A positioned edge after layout, with routed points */
export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    cssClass?: string;
    /** Connector variant at the source end — "multiple" spreads the edge into a ribbon. */
    sourceVariant?: ConnectorVariant;
    /** Connector variant at the target end — "multiple" spreads the edge into a ribbon. */
    targetVariant?: ConnectorVariant;
    points: { x: number; y: number }[];
}

/** Complete layout result ready for rendering */
export interface GraphLayout<TData = Record<string, unknown>> {
    nodes: GraphNode<TData>[];
    edges: GraphEdge[];
    width: number;
    height: number;
}
