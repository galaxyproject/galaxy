import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type NewStep, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { useWorkflowSearchStore } from "./workflowSearchStore";

const WORKFLOW_ID = "mock-workflow";

const toolStep: NewStep = {
    name: "FastQC",
    label: "quality_check",
    type: "tool",
    annotation: "QC tool",
    input_connections: {},
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
    tool_state: {},
    workflow_outputs: [],
};

function createEl(id: string) {
    const el = document.createElement("div");
    el.id = id;
    document.body.appendChild(el);
    return el;
}

function setupDom(stepId: number) {
    createEl("canvas-container");
    createEl(`wf-node-step-${stepId}`);
    createEl(`node-${stepId}-input-input1`);
    createEl(`node-${stepId}-output-html_file`);
}

describe("workflowSearchStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        document.body.innerHTML = "";
    });

    describe("search results", () => {
        it("finds a step by name", () => {
            const step = useWorkflowStepStore(WORKFLOW_ID).addStep(toolStep);
            setupDom(step.id);

            const results = useWorkflowSearchStore(WORKFLOW_ID).searchWorkflow("FastQC");

            expect(results.length).toBeGreaterThan(0);
            expect(results.some((r) => r.searchData.type === "step")).toBe(true);
        });

        it("finds a step by label", () => {
            const step = useWorkflowStepStore(WORKFLOW_ID).addStep(toolStep);
            setupDom(step.id);

            const results = useWorkflowSearchStore(WORKFLOW_ID).searchWorkflow("quality_check");

            expect(results.some((r) => r.searchData.type === "step")).toBe(true);
        });

        it("finds a step by annotation", () => {
            const step = useWorkflowStepStore(WORKFLOW_ID).addStep(toolStep);
            setupDom(step.id);

            const results = useWorkflowSearchStore(WORKFLOW_ID).searchWorkflow("QC tool");

            expect(results.some((r) => r.searchData.type === "step")).toBe(true);
        });

        it("returns empty results for a non-matching query", () => {
            const step = useWorkflowStepStore(WORKFLOW_ID).addStep(toolStep);
            setupDom(step.id);

            const results = useWorkflowSearchStore(WORKFLOW_ID).searchWorkflow("zzz-no-match");

            expect(results).toHaveLength(0);
        });

        it("finds input terminal by label", () => {
            const step = useWorkflowStepStore(WORKFLOW_ID).addStep(toolStep);
            setupDom(step.id);

            const results = useWorkflowSearchStore(WORKFLOW_ID).searchWorkflow("Input Dataset");

            expect(results.some((r) => r.searchData.type === "input")).toBe(true);
        });
    });

    describe("search cache (regression: ref-vs-null bug)", () => {
        it("does not crash on the first call when the cache is empty", () => {
            // Before the fix, `searchDataCacheData` (a Ref) was always truthy, so the
            // cache guard `&& searchDataCacheData` passed on the very first call and
            // returned null. Then searchWorkflow called null.map(...) → TypeError.
            const step = useWorkflowStepStore(WORKFLOW_ID).addStep(toolStep);
            setupDom(step.id);

            const searchStore = useWorkflowSearchStore(WORKFLOW_ID);
            expect(() => searchStore.searchWorkflow("FastQC")).not.toThrow();
            expect(searchStore.searchWorkflow("FastQC")).toBeInstanceOf(Array);
        });

        it("does not re-collect DOM data on a repeated call with the same changeId", () => {
            const step = useWorkflowStepStore(WORKFLOW_ID).addStep(toolStep);
            setupDom(step.id);

            const searchStore = useWorkflowSearchStore(WORKFLOW_ID);
            searchStore.searchWorkflow("FastQC"); // primes the cache

            const spy = vi.spyOn(document, "getElementById");
            searchStore.searchWorkflow("FastQC"); // should hit cache, skip DOM traversal
            expect(spy).not.toHaveBeenCalled();
            spy.mockRestore();
        });
    });
});
