import { describe, expect, it } from "vitest";

import { mockToolStep } from "@/components/Workflow/Editor/Actions/mockData";

import { removeOpenConnections } from "./removeOpenConnections";

describe("removeOpenConnections", () => {
    it("drops connections to steps outside the given steps", () => {
        const inside = { ...mockToolStep(0), input_connections: {} };
        const step = {
            ...mockToolStep(1),
            input_connections: { input1: [{ id: 0, output_name: "out_file1" }], input2: [{ id: 5, output_name: "x" }] },
        };

        const [, filtered] = removeOpenConnections([inside, step]);

        expect(filtered?.input_connections).toEqual({ input1: [{ id: 0, output_name: "out_file1" }] });
    });
});
