import { computed, type Ref } from "vue";

import type { WorkflowConnectionStore } from "@/stores/workflowConnectionStore";

/**
 * Given an active node and the connection store, returns the set of step IDs
 * that are in the upstream/downstream pipeline of the active node.
 * Returns `null` when no node is active (no filtering needed).
 */
export function useFocusedNodes(activeNodeId: Ref<number | null>, connectionStore: WorkflowConnectionStore) {
    const focusedNodeIds = computed((): Set<number> | null => {
        if (activeNodeId.value === null) {
            return null;
        }

        const visited = new Set<number>();
        visited.add(activeNodeId.value);

        // Two separate directional traversals are used to avoid including "sibling" steps:
        // e.g. if A→C and B→C, focusing on A should NOT include B (even though B feeds the same step C).

        // Upstream: walk backwards through output→input connections (find all ancestors)
        const upstreamQueue = [activeNodeId.value];
        while (upstreamQueue.length) {
            const stepId = upstreamQueue.shift()!;
            for (const conn of connectionStore.getConnectionsForStep(stepId)) {
                if (conn.input.stepId === stepId) {
                    const upstream = conn.output.stepId;
                    if (!visited.has(upstream)) {
                        visited.add(upstream);
                        upstreamQueue.push(upstream);
                    }
                }
            }
        }

        // Downstream: walk forwards through output→input connections (find all descendants)
        const downstreamQueue = [activeNodeId.value];
        while (downstreamQueue.length) {
            const stepId = downstreamQueue.shift()!;
            for (const conn of connectionStore.getConnectionsForStep(stepId)) {
                if (conn.output.stepId === stepId) {
                    const downstream = conn.input.stepId;
                    if (!visited.has(downstream)) {
                        visited.add(downstream);
                        downstreamQueue.push(downstream);
                    }
                }
            }
        }

        return visited;
    });

    return { focusedNodeIds };
}
