import { describe, expect, it } from "vitest";

import type { StepJobSummary } from "@/api/invocations";

import { getStepTitle, isTerminal, numTerminal } from "./util";

describe("getStepTitle", () => {
    it.each([
        { name: "tool label", index: 0, type: "tool", label: "My Label", expected: "Step 1: My Label" },
        { name: "input label", index: 2, type: "data_input", label: "Custom", expected: "Step 3: Custom" },
        { name: "first input", index: 0, type: "data_input", expected: "Step 1: Data input" },
        { name: "fifth input", index: 4, type: "data_input", expected: "Step 5: Data input" },
        { name: "named tool", index: 0, type: "tool", toolName: "FastQC", expected: "Step 1: FastQC" },
        { name: "unnamed tool", index: 0, type: "tool", expected: "Step 1: Unknown tool" },
        {
            name: "named subworkflow",
            index: 1,
            type: "subworkflow",
            subworkflowName: "My Subworkflow",
            expected: "Step 2: My Subworkflow",
        },
        { name: "unnamed subworkflow", index: 0, type: "subworkflow", expected: "Step 1: Subworkflow" },
        { name: "parameter input", index: 0, type: "parameter_input", expected: "Step 1: Parameter input" },
        { name: "data input", index: 0, type: "data_input", expected: "Step 1: Data input" },
        {
            name: "collection input",
            index: 0,
            type: "data_collection_input",
            expected: "Step 1: Data collection input",
        },
        {
            name: "unknown type",
            index: 0,
            type: "some_future_type",
            expected: "Step 1: Unknown step type 'some_future_type'",
        },
    ])("formats the title for a $name", ({ index, type, label, toolName, subworkflowName, expected }) => {
        expect(getStepTitle(index, type, label, toolName, subworkflowName)).toBe(expected);
    });
});

describe("numTerminal / isTerminal", () => {
    // A collection-mapped step: one `StepJobSummary` entry can represent many jobs at once, so
    // partial completion (some terminal, some still running) must be visible as a count, not just
    // a step-wide terminal/non-terminal flag.
    const partiallyDoneCollectionStep: StepJobSummary = {
        id: "collection1",
        model: "ImplicitCollectionJobs",
        populated_state: "ok",
        states: { ok: 2, running: 1 },
    };

    it("counts only terminal jobs within a partially-completed collection step", () => {
        expect(numTerminal(partiallyDoneCollectionStep)).toBe(2);
    });

    it("does not consider a step terminal while any job in it is still running", () => {
        expect(isTerminal(partiallyDoneCollectionStep)).toBe(false);
    });

    it("considers a step terminal once every job in it has a terminal state", () => {
        const fullyDoneCollectionStep: StepJobSummary = {
            id: "collection1",
            model: "ImplicitCollectionJobs",
            populated_state: "ok",
            states: { ok: 2, error: 1 },
        };

        expect(numTerminal(fullyDoneCollectionStep)).toBe(3);
        expect(isTerminal(fullyDoneCollectionStep)).toBe(true);
    });
});
