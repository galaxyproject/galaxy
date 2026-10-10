import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createTestStep } from "@/components/Workflow/Editor/test_fixtures";
import { type NewStep, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { setupTestPinia } from "./testUtils";
import { useWorkflowSearchStore } from "./workflowSearchStore";

const WORKFLOW_ID = "mock-workflow";

const toolStep: NewStep = {
    ...createTestStep(0, {
        inputs: [
            {
                name: "input1",
                label: "Input Dataset",
                input_type: "dataset",
                extensions: [],
                multiple: false,
                optional: false,
            },
        ],
        outputs: [{ name: "html_file", type: "data", multiple: false, optional: false, extensions: [] }],
    }),
    name: "FastQC",
    label: "quality_check",
    annotation: "QC tool",
};

function createEl(id: string) {
    const el = document.createElement("div");
    el.id = id;
    document.body.appendChild(el);
    return el;
}

function setupSearchWorkflow() {
    const step = useWorkflowStepStore(WORKFLOW_ID).addStep(toolStep);
    const stepId = step.id;
    createEl("canvas-container");
    createEl(`wf-node-step-${stepId}`);
    createEl(`node-${stepId}-input-input1`);
    createEl(`node-${stepId}-output-html_file`);
    return { step, searchStore: useWorkflowSearchStore(WORKFLOW_ID) };
}

describe("workflowSearchStore", () => {
    beforeEach(() => {
        setupTestPinia();
        document.body.innerHTML = "";
    });

    afterEach(() => {
        vi.restoreAllMocks();
        document.body.innerHTML = "";
    });

    describe("search results", () => {
        it.each([
            { field: "name", query: "FastQC" },
            { field: "label", query: "quality_check" },
            { field: "annotation", query: "QC tool" },
        ])("finds the step by its $field", ({ query }) => {
            const { step, searchStore } = setupSearchWorkflow();

            const results = searchStore.searchWorkflow(query);

            expect(results.length).toBeGreaterThan(0);
            expect(results).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        searchData: expect.objectContaining({ type: "step", stepId: String(step.id) }),
                    }),
                ]),
            );
        });

        it("returns empty results for a non-matching query", () => {
            const { searchStore } = setupSearchWorkflow();

            const results = searchStore.searchWorkflow("zzz-no-match");

            expect(results).toHaveLength(0);
        });

        it("finds input terminal by label", () => {
            const { searchStore } = setupSearchWorkflow();

            const results = searchStore.searchWorkflow("Input Dataset");

            expect(results).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        searchData: expect.objectContaining({ type: "input", label: "Input Dataset" }),
                    }),
                ]),
            );
        });
    });

    describe("search cache (regression: ref-vs-null bug)", () => {
        it("does not crash on the first call when the cache is empty", () => {
            // A truthy Ref used to let a null cache through on the first search.
            const { searchStore } = setupSearchWorkflow();

            expect(() => searchStore.searchWorkflow("FastQC")).not.toThrow();
            expect(searchStore.searchWorkflow("FastQC")).toBeInstanceOf(Array);
        });

        it("does not re-collect DOM data on a repeated call with the same changeId", () => {
            const { searchStore } = setupSearchWorkflow();

            searchStore.searchWorkflow("FastQC"); // primes the cache

            const spy = vi.spyOn(document, "getElementById");
            searchStore.searchWorkflow("FastQC"); // should hit cache, skip DOM traversal
            expect(spy).not.toHaveBeenCalled();
        });
    });
});
