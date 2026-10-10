import { describe, expect, it, vi } from "vitest";

import { getRequiredLabels, getRequiredObject, hasValidLabel, hasValidName, hasValidObject } from "./requirements";

vi.mock("./requirements.yml", () => ({
    default: {
        history_dataset_id: ["tool_a", "tool_b"],
        history_dataset_collection_id: ["tool_c"],
        job_id: ["tool_d"],
        none: ["tool_x", "tool_y"],
    },
}));

const WORKFLOW_LABELS = [
    { type: "input", label: "A" },
    { type: "output", label: "B" },
    { type: "step", label: "S" },
];

describe("requirements utils", () => {
    describe("getRequiredObject", () => {
        it.each([
            ["tool_a", "history_dataset_id"],
            ["tool_c", "history_dataset_collection_id"],
            ["tool_d", "job_id"],
        ])("returns the object type listed for %s", (name, objectType) => {
            expect(getRequiredObject(name)).toBe(objectType);
        });

        it("returns null for a tool listed under 'none'", () => {
            expect(getRequiredObject("tool_x")).toBeNull();
        });

        it.each([["nonexistent_tool"], [undefined]])("returns null for unknown tool %s", (name) => {
            expect(getRequiredObject(name)).toBeNull();
        });
    });

    describe("getRequiredLabels", () => {
        it.each([
            ["history_dataset_id", ["input", "output"]],
            ["history_dataset_collection_id", ["input", "output"]],
            ["job_id", ["step"]],
        ])("returns the label types required for %s", (objectType, labelTypes) => {
            expect(getRequiredLabels(objectType)).toEqual(labelTypes);
        });

        it("returns no label types when no object is required", () => {
            expect(getRequiredLabels(null)).toEqual([]);
        });

        it("returns no label types for an object type without label requirements", () => {
            expect(getRequiredLabels("history_id")).toEqual([]);
        });
    });

    describe("hasValidLabel", () => {
        it("accepts arguments where exactly one required label matches a workflow label", () => {
            expect(hasValidLabel("tool_a", { input: "A", output: "Wrong" }, WORKFLOW_LABELS)).toBe(true);
        });

        it("rejects arguments where no required label matches a workflow label", () => {
            expect(hasValidLabel("tool_a", { input: "X", output: "Y" }, WORKFLOW_LABELS)).toBe(false);
        });

        it("rejects arguments where both input and output labels match workflow labels", () => {
            expect(hasValidLabel("tool_a", { input: "A", output: "B" }, WORKFLOW_LABELS)).toBe(false);
        });

        it.each([
            ["a 'none' tool", "tool_x"],
            ["an unknown tool", "nonexistent_tool"],
        ])("accepts empty arguments for %s, which requires no labels", (_description, name) => {
            expect(hasValidLabel(name, {}, WORKFLOW_LABELS)).toBe(true);
        });

        it("accepts any arguments when workflow labels are undefined", () => {
            expect(hasValidLabel("tool_d", { step: "S" }, undefined)).toBe(true);
        });
    });

    describe("hasValidObject", () => {
        it.each([
            ["tool_a", { history_dataset_id: "abc" }],
            ["tool_d", { job_id: "abc" }],
        ])("accepts %s when its required object is present", (name, args) => {
            expect(hasValidObject(name, args)).toBe(true);
        });

        it.each([["tool_a"], ["tool_d"]])("rejects %s when its required object is missing", (name) => {
            expect(hasValidObject(name, {})).toBe(false);
        });

        it("accepts history_dataset_collection_id where history_dataset_id is required", () => {
            expect(hasValidObject("tool_a", { history_dataset_collection_id: "abc" })).toBe(true);
        });

        it("accepts implicit_collection_jobs_id where job_id is required", () => {
            expect(hasValidObject("tool_d", { implicit_collection_jobs_id: "abc" })).toBe(true);
        });
    });

    describe("hasValidName", () => {
        it.each([["tool_a"], ["tool_c"], ["tool_x"]])("accepts listed tool %s", (name) => {
            expect(hasValidName(name)).toBe(true);
        });

        it.each([["some_unknown_tool"], [undefined]])("rejects unknown tool %s", (name) => {
            expect(hasValidName(name)).toBe(false);
        });
    });
});
