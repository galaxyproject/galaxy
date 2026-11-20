import { describe, expect, it } from "vitest";

import { mockToolStep } from "@/components/Workflow/Editor/Actions/mockData";
import type { Step } from "@/stores/workflowStepStore";

import { getTraversedSelection } from "./traversedSelection";

// 0 → 1 → 2, plus 3 → 2 from an unselected branch
function chainSteps(): Record<number, Step> {
    const link = (id: number) => ({ input1: [{ id, output_name: "out_file1" }] });
    return {
        0: { ...mockToolStep(0), input_connections: {} },
        1: { ...mockToolStep(1), input_connections: link(0) },
        2: { ...mockToolStep(2), input_connections: { ...link(1), input2: [{ id: 3, output_name: "out_file1" }] } },
        3: { ...mockToolStep(3), input_connections: {} },
    };
}

describe("getTraversedSelection", () => {
    it("adds steps between selected steps and leaves unrelated branches out", () => {
        expect(getTraversedSelection([0, 2], chainSteps()).sort()).toEqual([0, 1, 2]);
    });

    it("keeps a selection without in-between steps unchanged", () => {
        expect(getTraversedSelection([1, 2], chainSteps()).sort()).toEqual([1, 2]);
    });

    it("explores shared upstream steps once, so long split-and-merge chains stay fast", () => {
        // 30 times: a step splits into two branches that merge again; none lead back to the selection
        const steps: Record<number, Step> = { 0: { ...mockToolStep(0), input_connections: {} } };
        let join = 0;
        for (let layer = 0; layer < 30; layer++) {
            const [left, right, nextJoin] = [join + 1, join + 2, join + 3];
            const from = (id: number) => [{ id, output_name: "out_file1" }];
            steps[left] = { ...mockToolStep(left), input_connections: { input1: from(join) } };
            steps[right] = { ...mockToolStep(right), input_connections: { input1: from(join) } };
            steps[nextJoin] = { ...mockToolStep(nextJoin), input_connections: { a: from(left), b: from(right) } };
            join = nextJoin;
        }

        expect(getTraversedSelection([join], steps)).toEqual([join]);
    });
});
