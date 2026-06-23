import { describe, expect, it } from "vitest";

import { getStepTitle } from "./util";

describe("getStepTitle", () => {
    it("uses label when provided, regardless of type", () => {
        expect(getStepTitle(0, "tool", "My Label")).toBe("Step 1: My Label");
        expect(getStepTitle(2, "data_input", "Custom")).toBe("Step 3: Custom");
    });

    it("uses 1-based step index", () => {
        expect(getStepTitle(0, "data_input")).toBe("Step 1: Data input");
        expect(getStepTitle(4, "data_input")).toBe("Step 5: Data input");
    });

    it("formats tool step with tool name", () => {
        expect(getStepTitle(0, "tool", undefined, "FastQC")).toBe("Step 1: FastQC");
    });

    it("uses 'Unknown tool' default when tool name omitted", () => {
        expect(getStepTitle(0, "tool")).toBe("Step 1: Unknown tool");
    });

    it("formats subworkflow step with subworkflow name", () => {
        expect(getStepTitle(1, "subworkflow", undefined, undefined, "My Subworkflow")).toBe("Step 2: My Subworkflow");
    });

    it("uses 'Subworkflow' default when subworkflow name omitted", () => {
        expect(getStepTitle(0, "subworkflow")).toBe("Step 1: Subworkflow");
    });

    it("formats input types correctly", () => {
        expect(getStepTitle(0, "parameter_input")).toBe("Step 1: Parameter input");
        expect(getStepTitle(0, "data_input")).toBe("Step 1: Data input");
        expect(getStepTitle(0, "data_collection_input")).toBe("Step 1: Data collection input");
    });

    it("handles unknown step types", () => {
        expect(getStepTitle(0, "some_future_type")).toBe("Step 1: Unknown step type 'some_future_type'");
    });
});
