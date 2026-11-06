import { describe, expect, it, vi } from "vitest";

import { mockToolStep } from "@/components/Workflow/Editor/Actions/mockData";
import type { WorkflowSearchStore } from "@/stores/workflowSearchStore";
import type { Step } from "@/stores/workflowStepStore";

import { convertOpenConnections } from "./convertOpenConnections";

vi.mock("@/components/Workflow/Editor/modules/services", () => ({
    getModule: vi.fn(async () => ({
        tool_state: {},
        inputs: [],
        outputs: [{ name: "output", extensions: ["input"], optional: false }],
        config_form: {},
    })),
}));

const searchStore = { findOutputPosition: () => ({ x: 0, y: 0 }) } as unknown as WorkflowSearchStore;

describe("convertOpenConnections", () => {
    it("rewrites open input connections on copies, leaving the editor's steps untouched", async () => {
        const allSteps: Record<number, Step> = {
            0: mockToolStep(0),
            1: { ...mockToolStep(1), input_connections: { input1: [{ id: 0, output_name: "out_file1" }] } },
        };
        const before = structuredClone(allSteps);

        const { stepArray } = await convertOpenConnections([1], allSteps, searchStore);

        expect(allSteps).toEqual(before);
        const copiedStep = stepArray.find((step) => step.type === "tool");
        expect(copiedStep?.input_connections.input1).toEqual([{ id: 0, output_name: "output" }]);
    });
});
