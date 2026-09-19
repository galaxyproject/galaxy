import { computed, type Ref } from "vue";

/** Graph adjacency lookups for a node id. */
export interface FocusAdjacency<T> {
    /** Immediate upstream (parent) node ids of `id`. */
    upstream: (id: T) => Iterable<T>;
    /** Immediate downstream (child) node ids of `id`. */
    downstream: (id: T) => Iterable<T>;
}

/**
 * Given an active node, returns the set of node ids in its upstream and
 * downstream lineage (active node + all ancestors + all descendants).
 * Returns null when no node is active — caller treats null as "no filtering,
 * nothing dimmed".
 *
 * Two separate directional BFS walks avoid sibling pollution: if A→C and B→C,
 * focusing on A includes A and C but NOT B.
 */
export function useFocusedNodes<T>(activeNodeId: Ref<T | null>, adjacency: FocusAdjacency<T>) {
    const focusedNodeIds = computed((): Set<T> | null => {
        if (activeNodeId.value === null) {
            return null;
        }

        const visited = new Set<T>();
        visited.add(activeNodeId.value);

        const upstreamQueue: T[] = [activeNodeId.value];
        while (upstreamQueue.length) {
            const id = upstreamQueue.shift()!;
            for (const upstream of adjacency.upstream(id)) {
                if (!visited.has(upstream)) {
                    visited.add(upstream);
                    upstreamQueue.push(upstream);
                }
            }
        }

        const downstreamQueue: T[] = [activeNodeId.value];
        while (downstreamQueue.length) {
            const id = downstreamQueue.shift()!;
            for (const downstream of adjacency.downstream(id)) {
                if (!visited.has(downstream)) {
                    visited.add(downstream);
                    downstreamQueue.push(downstream);
                }
            }
        }

        return visited;
    });

    return { focusedNodeIds };
}
