import { describe, expect, it } from "vitest";

import type { StepJobSummary } from "@/api/invocations";

import { getStepTitle, isTerminal, numTerminal } from "./util";

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

describe("numTerminal / isTerminal", () => {
    // A collection-mapped step: one `StepJobSummary` entry can represent many jobs at once, so
    // partial completion (some terminal, some still running) must be visible as a count, not just
    // a step-wide terminal/non-terminal flag.
    const partiallyDoneCollectionStep = {
        id: "collection1",
        model: "ImplicitCollectionJobs",
        states: { ok: 2, running: 1 },
    } as unknown as StepJobSummary;

    it("counts only terminal jobs within a partially-completed collection step", () => {
        expect(numTerminal(partiallyDoneCollectionStep)).toBe(2);
    });

    it("does not consider a step terminal while any job in it is still running", () => {
        expect(isTerminal(partiallyDoneCollectionStep)).toBe(false);
    });

    it("considers a step terminal once every job in it has a terminal state", () => {
        const fullyDoneCollectionStep = {
            id: "collection1",
            model: "ImplicitCollectionJobs",
            states: { ok: 2, error: 1 },
        } as unknown as StepJobSummary;

        expect(numTerminal(fullyDoneCollectionStep)).toBe(3);
        expect(isTerminal(fullyDoneCollectionStep)).toBe(true);
    });
});
