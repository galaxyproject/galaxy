import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";

/** A labeled port on a graph node (input or output connector) */
export interface GraphNodePort {
    name: string;
    label: string;
}

/** A positioned node after layout */
export interface GraphNode {
    id: string;
    x: number;
    y: number;
    width: number;
    height: number;
    label: string;
    icon: IconDefinition;
    badge?: string | null;
    cssClass?: string;
    /** Input ports displayed in the node body */
    inputs?: GraphNodePort[];
    /** Output ports displayed in the node body */
    outputs?: GraphNodePort[];
    /** Arbitrary domain data attached by the mapper */
    data?: Record<string, unknown>;
}

/** A positioned edge after layout, with routed points */
export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    cssClass?: string;
    /** Render as a collection ribbon (multiple parallel lines) */
    isCollection?: boolean;
    points: { x: number; y: number }[];
}

/** Edge rendering style */
export type EdgeStyle = "orthogonal" | "curved";

/** Complete layout result ready for rendering */
export interface GraphLayout {
    nodes: GraphNode[];
    edges: GraphEdge[];
    width: number;
    height: number;
}
