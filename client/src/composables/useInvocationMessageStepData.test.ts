import { describe, expect, it } from "vitest";

import { generateStepLabel } from "./useInvocationMessageStepData";

describe("generateStepLabel", () => {
    it("returns basic step label when no additional info available", () => {
        const step = { type: "tool" };
        expect(generateStepLabel(0, step)).toBe("Step 1");
        expect(generateStepLabel(2, step)).toBe("Step 3");
    });

    it("includes step label when available", () => {
        const step = { type: "tool", label: "My Step" };
        expect(generateStepLabel(0, step)).toBe("1:My Step");
        expect(generateStepLabel(4, step)).toBe("5:My Step");
    });

    it("extracts last segment from tool_id for tool steps", () => {
        const step = { type: "tool", tool_id: "toolshed.g2.bx.psu.edu/repos/owner/cat1" };
        expect(generateStepLabel(0, step)).toBe("1:cat1");
    });

    it("uses full tool_id when no slash present", () => {
        const step = { type: "tool", tool_id: "cat1" };
        expect(generateStepLabel(0, step)).toBe("1:cat1");
    });

    it("labels subworkflow steps appropriately", () => {
        const step = { type: "subworkflow" };
        expect(generateStepLabel(1, step)).toBe("2:subworkflow");
    });

    it("prefers label over tool_id", () => {
        const step = { type: "tool", label: "Custom Name", tool_id: "cat1" };
        expect(generateStepLabel(0, step)).toBe("1:Custom Name");
    });
});
