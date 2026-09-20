import { describe, expect, it } from "vitest";
import { shallowRef } from "vue";

import { type FocusAdjacency, useFocusedNodes } from "./useFocusedNodes";

/** Build an adjacency from a flat list of [source, target] edges. */
function adjacencyFor<T>(edges: [T, T][]): FocusAdjacency<T> {
    return {
        upstream(id) {
            return edges.filter(([, t]) => t === id).map(([s]) => s);
        },
        downstream(id) {
            return edges.filter(([s]) => s === id).map(([, t]) => t);
        },
    };
}

function focused<T>(activeNodeId: T | null, edges: [T, T][]): Set<T> | null {
    const { focusedNodeIds } = useFocusedNodes(shallowRef<T | null>(activeNodeId), adjacencyFor(edges));
    return focusedNodeIds.value;
}

describe("useFocusedNodes", () => {
    it("returns null when no node is active", () => {
        expect(focused<number>(null, [[0, 1]])).toBeNull();
    });

    it("includes only the active node when it has no connections", () => {
        expect(focused(0, [])).toEqual(new Set([0]));
    });

    it("includes full linear chain when focusing the middle node (A→B→C, focus B)", () => {
        expect(
            focused(1, [
                [0, 1],
                [1, 2],
            ]),
        ).toEqual(new Set([0, 1, 2]));
    });

    it("includes full linear chain when focusing the start node (A→B→C, focus A)", () => {
        expect(
            focused(0, [
                [0, 1],
                [1, 2],
            ]),
        ).toEqual(new Set([0, 1, 2]));
    });

    it("excludes sibling inputs — A→C and B→C: focusing A excludes B", () => {
        // A(0) → C(2) ← B(1)
        expect(
            focused(0, [
                [0, 2],
                [1, 2],
            ]),
        ).toEqual(new Set([0, 2]));
    });

    it("excludes sibling outputs — A→B and A→C: focusing C excludes B", () => {
        // B(1) ← A(0) → C(2)
        expect(
            focused(2, [
                [0, 1],
                [0, 2],
            ]),
        ).toEqual(new Set([0, 2]));
    });

    it("handles diamond — A→B→D and A→C→D: focusing B excludes C", () => {
        // A(0) → B(1) → D(3)
        //      ↘ C(2) ↗
        expect(
            focused(1, [
                [0, 1],
                [0, 2],
                [1, 3],
                [2, 3],
            ]),
        ).toEqual(new Set([0, 1, 3]));
    });

    it("works with string ids", () => {
        expect(
            focused("b", [
                ["a", "b"],
                ["b", "c"],
            ]),
        ).toEqual(new Set(["a", "b", "c"]));
    });
});
