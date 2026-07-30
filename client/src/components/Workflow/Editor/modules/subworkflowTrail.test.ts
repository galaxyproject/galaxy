import { describe, expect, it } from "vitest";

import { encodeSubworkflowTrail, parseSubworkflowTrail } from "./subworkflowTrail";

describe("subworkflowTrail", () => {
    it("round trips a trail", () => {
        const trail = [
            { workflowId: "abc123", stepOrderIndex: 2 },
            { workflowId: "def456", stepOrderIndex: 0 },
        ];
        expect(parseSubworkflowTrail(encodeSubworkflowTrail(trail))).toEqual(trail);
    });

    it("treats an absent trail as empty", () => {
        expect(parseSubworkflowTrail(undefined)).toEqual([]);
        expect(parseSubworkflowTrail(null)).toEqual([]);
        expect(parseSubworkflowTrail("")).toEqual([]);
    });

    it("drops malformed entries instead of throwing", () => {
        const trail = parseSubworkflowTrail("abc123:2,nostep,def456:notanumber,ghi789:1");
        expect(trail).toEqual([
            { workflowId: "abc123", stepOrderIndex: 2 },
            { workflowId: "ghi789", stepOrderIndex: 1 },
        ]);
    });

    it("keeps step zero, which is falsy", () => {
        expect(parseSubworkflowTrail("abc123:0")).toEqual([{ workflowId: "abc123", stepOrderIndex: 0 }]);
    });
});
