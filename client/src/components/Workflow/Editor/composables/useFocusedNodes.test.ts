import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import { ref } from "vue";

import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { type NewStep, useWorkflowStepStore } from "@/stores/workflowStepStore";
import type { Connection } from "@/stores/workflowStoreTypes";

import { useFocusedNodes } from "./useFocusedNodes";

const WORKFLOW_ID = "test-workflow";

const baseStep: NewStep = {
    input_connections: {},
    inputs: [],
    name: "step",
    outputs: [],
    post_job_actions: {},
    tool_state: {},
    type: "tool",
    workflow_outputs: [],
};

/** Build a connection from outputStepId → inputStepId */
function conn(outputStepId: number, inputStepId: number): Connection {
    return {
        output: { stepId: outputStepId, name: "out", connectorType: "output" },
        input: { stepId: inputStepId, name: "in", connectorType: "input" },
    };
}

describe("useFocusedNodes", () => {
    let connectionStore: ReturnType<typeof useConnectionStore>;
    let stepStore: ReturnType<typeof useWorkflowStepStore>;

    beforeEach(() => {
        setActivePinia(createPinia());
        stepStore = useWorkflowStepStore(WORKFLOW_ID);
        connectionStore = useConnectionStore(WORKFLOW_ID);
    });

    /** Add n steps to the store (IDs are assigned 0..n-1) */
    function addSteps(n: number) {
        for (let i = 0; i < n; i++) {
            stepStore.addStep({ ...baseStep, name: `Step ${i}` });
        }
    }

    /** Convenience: call the composable and return the computed value */
    function focused(activeNodeId: number | null): Set<number> | null {
        const { focusedNodeIds } = useFocusedNodes(ref(activeNodeId), connectionStore);
        return focusedNodeIds.value;
    }

    it("returns null when no node is active", () => {
        addSteps(2);
        connectionStore.addConnection(conn(0, 1));
        expect(focused(null)).toBeNull();
    });

    it("includes only the active node when it has no connections", () => {
        addSteps(1);
        expect(focused(0)).toEqual(new Set([0]));
    });

    it("includes full linear chain when focusing the middle node (A→B→C, focus B)", () => {
        addSteps(3);
        connectionStore.addConnection(conn(0, 1)); // A→B
        connectionStore.addConnection(conn(1, 2)); // B→C
        expect(focused(1)).toEqual(new Set([0, 1, 2]));
    });

    it("includes full linear chain when focusing the start node (A→B→C, focus A)", () => {
        addSteps(3);
        connectionStore.addConnection(conn(0, 1)); // A→B
        connectionStore.addConnection(conn(1, 2)); // B→C
        expect(focused(0)).toEqual(new Set([0, 1, 2]));
    });

    it("excludes sibling inputs — A→C and B→C: focusing A should not include B", () => {
        // A(0) → C(2) ← B(1)
        addSteps(3);
        connectionStore.addConnection(conn(0, 2)); // A→C
        connectionStore.addConnection(conn(1, 2)); // B→C
        expect(focused(0)).toEqual(new Set([0, 2]));
    });

    it("excludes sibling outputs — A→B and A→C: focusing C should not include B", () => {
        // B(1) ← A(0) → C(2)
        addSteps(3);
        connectionStore.addConnection(conn(0, 1)); // A→B
        connectionStore.addConnection(conn(0, 2)); // A→C
        expect(focused(2)).toEqual(new Set([0, 2]));
    });

    it("handles diamond — A→B→D and A→C→D: focusing B excludes C", () => {
        // A(0) → B(1) → D(3)
        //      ↘ C(2) ↗
        addSteps(4);
        connectionStore.addConnection(conn(0, 1)); // A→B
        connectionStore.addConnection(conn(0, 2)); // A→C
        connectionStore.addConnection(conn(1, 3)); // B→D
        connectionStore.addConnection(conn(2, 3)); // C→D
        expect(focused(1)).toEqual(new Set([0, 1, 3])); // A, B, D — not C
    });
});
