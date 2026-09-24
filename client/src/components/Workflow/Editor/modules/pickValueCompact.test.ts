import { describe, expect, it } from "vitest";

import { computePickValueCompaction } from "./pickValueCompact";

describe("computePickValueCompaction", () => {
    it("no renames when disconnecting last of 3", () => {
        const connections = {
            input_0: { id: 1, output_name: "out" },
            input_1: { id: 2, output_name: "out" },
            input_2: { id: 3, output_name: "out" },
        };
        const result = computePickValueCompaction(connections, "input_2");
        expect(result.renames).toEqual([]);
    });

    it("one rename when disconnecting middle of 3", () => {
        const connections = {
            input_0: { id: 1, output_name: "out" },
            input_1: { id: 2, output_name: "out" },
            input_2: { id: 3, output_name: "out" },
        };
        const result = computePickValueCompaction(connections, "input_1");
        expect(result.renames).toEqual([{ from: "input_2", to: "input_1" }]);
    });

    it("three renames when disconnecting first of 4", () => {
        const connections = {
            input_0: { id: 1, output_name: "out" },
            input_1: { id: 2, output_name: "out" },
            input_2: { id: 3, output_name: "out" },
            input_3: { id: 4, output_name: "out" },
        };
        const result = computePickValueCompaction(connections, "input_0");
        expect(result.renames).toEqual([
            { from: "input_1", to: "input_0" },
            { from: "input_2", to: "input_1" },
            { from: "input_3", to: "input_2" },
        ]);
    });

    it("no renames when disconnecting only connection", () => {
        const connections = {
            input_0: { id: 1, output_name: "out" },
        };
        const result = computePickValueCompaction(connections, "input_0");
        expect(result.renames).toEqual([]);
    });

    it("no renames with empty connections", () => {
        const result = computePickValueCompaction({}, "input_0");
        expect(result.renames).toEqual([]);
    });

    it("ignores non-input keys", () => {
        const connections = {
            input_0: { id: 1, output_name: "out" },
            input_1: { id: 2, output_name: "out" },
            input_2: { id: 3, output_name: "out" },
            someOtherKey: { id: 99, output_name: "other" },
        };
        const result = computePickValueCompaction(connections, "input_1");
        expect(result.renames).toEqual([{ from: "input_2", to: "input_1" }]);
    });

    it("ignores null/undefined connection values", () => {
        const connections: Record<string, unknown> = {
            input_0: { id: 1, output_name: "out" },
            input_1: null,
            input_2: { id: 3, output_name: "out" },
        };
        const result = computePickValueCompaction(connections, "input_1");
        expect(result.renames).toEqual([{ from: "input_2", to: "input_1" }]);
    });
});
