import type { HistoryGraphNode } from "./historyGraphMapper";

// State colors resolved lazily from the global `--state-color-*` custom
// properties defined in base.scss.
const stateColors: Record<string, string> = {};

function stateColor(state: string): string {
    if (!(state in stateColors)) {
        stateColors[state] = getComputedStyle(document.documentElement)
            .getPropertyValue(`--state-color-${state.replace(/_/g, "-")}`)
            .trim();
    }
    return stateColors[state]!;
}

/** Minimap fill color for a history graph node, keyed off its display state. */
export function historyNodeColor(node: HistoryGraphNode): string | null {
    if (node.data?.src === "tool_request") {
        return null;
    }
    const state = node.data?.state;
    return (state && stateColor(state)) || null;
}
