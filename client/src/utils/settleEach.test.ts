import { describe, expect, it } from "vitest";

import { describeFailures, settleEach } from "./settleEach";

describe("settleEach", () => {
    it("runs every item in order and continues past failures", async () => {
        const seen: number[] = [];
        const operation = async (n: number) => {
            seen.push(n);
            if (n === 2) {
                throw new Error("boom");
            }
        };
        const failures = await settleEach([1, 2, 3], operation);
        expect(seen).toEqual([1, 2, 3]);
        expect(failures).toEqual([{ item: 2, error: "boom" }]);
    });

    it("returns no failures when every operation succeeds", async () => {
        expect(await settleEach(["a", "b"], async () => undefined)).toEqual([]);
    });

    it("iterates a snapshot so mutating the source mid-run has no effect", async () => {
        const items = [1, 2, 3];
        const seen: number[] = [];
        await settleEach(items, async (n) => {
            seen.push(n);
            items.length = 0;
        });
        expect(seen).toEqual([1, 2, 3]);
    });
});

describe("describeFailures", () => {
    it("joins named failures with their errors", () => {
        const failures = [
            { item: { name: "x" }, error: "e1" },
            { item: { name: "y" }, error: "e2" },
        ];
        expect(describeFailures(failures, (i) => i.name)).toBe("'x' (e1), 'y' (e2)");
    });
});
