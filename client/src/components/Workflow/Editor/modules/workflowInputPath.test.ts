import { describe, expect, it } from "vitest";

import { connectionNameToInputPath, inputPathIsPrefix, resolveConnectionNameToInputPath } from "./workflowInputPath";

describe("workflow input paths", () => {
    it("maps flat connection names to nested expression paths", () => {
        expect(connectionNameToInputPath("cond|input1")).toEqual(["cond", "input1"]);
    });

    it("compares complete path segments", () => {
        expect(inputPathIsPrefix(["cond"], ["cond", "input1"])).toBe(true);
        expect(inputPathIsPrefix(["cond", "input1"], ["cond", "input10"])).toBe(false);
    });

    it("resolves repeat indices from tool state", () => {
        const state = { queries: '[{"__index__": 0, "input2": {}}]' };
        expect(resolveConnectionNameToInputPath("queries_0|input2", state)).toEqual(["queries", 0, "input2"]);
    });

    it("resolves nested repeats", () => {
        const state = { outer: [{ inner: [{}, { param: {} }] }] };
        expect(resolveConnectionNameToInputPath("outer_0|inner_1|param", state)).toEqual([
            "outer",
            0,
            "inner",
            1,
            "param",
        ]);
    });

    it("preserves a literal name that looks like a repeat", () => {
        const state = { outer_0: { param: {} } };
        expect(resolveConnectionNameToInputPath("outer_0|param", state)).toEqual(["outer_0", "param"]);
    });

    it("declines a genuinely ambiguous flattened name", () => {
        const state = { outer_0: { param: {} }, outer: [{ param: {} }] };
        expect(resolveConnectionNameToInputPath("outer_0|param", state)).toBeNull();
    });

    it("declines when no state path matches", () => {
        expect(resolveConnectionNameToInputPath("queries_0|input2", {})).toBeNull();
    });
});
