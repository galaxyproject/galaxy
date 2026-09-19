import { describe, expect, it, vi } from "vitest";

import { getRequiredLabels, getRequiredObject, hasValidLabel, hasValidName, hasValidObject } from "./requirements";

vi.mock(
    "./requirements.yml",
    () => ({
        default: {
            history_dataset_id: ["tool_a", "tool_b"],
            history_dataset_collection_id: ["tool_c"],
            job_id: ["tool_d"],
            none: ["tool_x", "tool_y"],
        },
    }),
    { virtual: true },
);

describe("requirements utils", () => {
    describe("getRequiredObject", () => {
        it("returns correct object type for known tool", () => {
            expect(getRequiredObject("tool_a")).toBe("history_dataset_id");
            expect(getRequiredObject("tool_c")).toBe("history_dataset_collection_id");
            expect(getRequiredObject("tool_d")).toBe("job_id");
        });

        it("returns null for 'none' type", () => {
            expect(getRequiredObject("tool_x")).toBeNull();
        });

        it("returns null for unknown tool", () => {
            expect(getRequiredObject("nonexistent_tool")).toBeNull();
            expect(getRequiredObject(undefined)).toBeNull();
        });
    });

    describe("getRequiredLabels", () => {
        it("returns expected labels for known types", () => {
            expect(getRequiredLabels(getRequiredObject("tool_a"))).toEqual(["input", "output"]);
            expect(getRequiredLabels(getRequiredObject("tool_c"))).toEqual(["input", "output"]);
            expect(getRequiredLabels(getRequiredObject("tool_d"))).toEqual(["step"]);
        });

        it("returns empty array for unknown or none", () => {
            expect(getRequiredLabels(getRequiredObject("tool_x"))).toEqual([]);
            expect(getRequiredLabels(getRequiredObject("nonexistent_tool"))).toEqual([]);
        });
    });

    describe("hasValidLabel", () => {
        const labels = [
            { type: "input", label: "A" },
            { type: "output", label: "B" },
            { type: "step", label: "S" },
        ];

        it("returns true when at least one required label is present", () => {
            const args = { input: "A", output: "Wrong" };
            expect(hasValidLabel("tool_a", args, labels)).toBe(true);
        });

        it("returns false when none of the required labels are matched", () => {
            const args = { input: "X", output: "Y" };
            expect(hasValidLabel("tool_a", args, labels)).toBe(false);
        });

        it("returns true when no required labels for the tool", () => {
            const args = {};
            expect(hasValidLabel("tool_x", args, labels)).toBe(true);
        });

        it("returns true when labels are undefined", () => {
            const args = { step: "S" };
            expect(hasValidLabel("tool_d", args, undefined)).toBe(true);
        });

        it("returns true when requiredLabels is empty", () => {
            const args = {};
            expect(hasValidLabel("nonexistent_tool", args, labels)).toBe(true);
        });
    });

    describe("hasValidObject", () => {
        it("returns true when required object is present", () => {
            expect(hasValidObject("tool_a", { history_dataset_id: "abc" })).toBe(true);
            expect(hasValidObject("tool_d", { job_id: "abc" })).toBe(true);
        });

        it("returns false when required object is missing", () => {
            expect(hasValidObject("tool_a", {})).toBe(false);
            expect(hasValidObject("tool_d", {})).toBe(false);
        });

        it("accepts history_dataset_collection_id where history_dataset_id is required", () => {
            expect(hasValidObject("tool_a", { history_dataset_collection_id: "abc" })).toBe(true);
        });

        it("accepts implicit_collection_jobs_id where job_id is required", () => {
            expect(hasValidObject("tool_d", { implicit_collection_jobs_id: "abc" })).toBe(true);
        });
    });

    describe("hasValidName", () => {
        it("returns true for known tools", () => {
            expect(hasValidName("tool_a")).toBe(true);
            expect(hasValidName("tool_c")).toBe(true);
            expect(hasValidName("tool_x")).toBe(true);
        });

        it("returns false for unknown tool or undefined", () => {
            expect(hasValidName("some_unknown_tool")).toBe(false);
            expect(hasValidName(undefined)).toBe(false);
        });
    });
});
