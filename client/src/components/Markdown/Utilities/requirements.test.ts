import type { WorkflowLabel } from "@/components/Markdown/Editor/types";

import { getRequiredLabels, getRequiredObject, hasValidLabel, hasValidName } from "./requirements";

jest.mock(
    "./requirements.yml",
    () => ({
        history_dataset_id: ["tool_a", "tool_b"],
        history_dataset_collection_id: ["tool_c"],
        job_id: ["tool_d"],
        none: ["tool_x", "tool_y"],
    }),
    { virtual: true }
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
            expect(getRequiredLabels("tool_a")).toEqual(["input", "output"]);
            expect(getRequiredLabels("tool_c")).toEqual(["input", "output"]);
            expect(getRequiredLabels("tool_d")).toEqual(["step"]);
        });

        it("returns empty array for unknown or none", () => {
            expect(getRequiredLabels("tool_x")).toEqual([]);
            expect(getRequiredLabels("nonexistent_tool")).toEqual([]);
        });
    });

    describe("hasValidLabel", () => {
        const labels: WorkflowLabel[] = [
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
            expect(hasValidLabel("tool_d", args, undefined as any)).toBe(true);
        });

        it("returns true when requiredLabels is empty", () => {
            const args = {};
            expect(hasValidLabel("nonexistent_tool", args, labels)).toBe(true);
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
