import { describe, expect, it, vi } from "vitest";

import { pollUntil } from "./pollUntil";

describe("pollUntil", () => {
    it("should return immediately when condition is met on first call", async () => {
        const fn = vi.fn().mockResolvedValue("done");
        const result = await pollUntil({
            fn,
            condition: (v) => v === "done",
        });
        expect(result).toBe("done");
        expect(fn).toHaveBeenCalledTimes(1);
    });

    it("should poll until condition is met", async () => {
        let callCount = 0;
        const fn = vi.fn().mockImplementation(async () => {
            callCount++;
            return callCount >= 3 ? "ready" : "pending";
        });
        const result = await pollUntil({
            fn,
            condition: (v) => v === "ready",
            interval: 10,
        });
        expect(result).toBe("ready");
        expect(fn).toHaveBeenCalledTimes(3);
    });

    it("should throw on timeout", async () => {
        const fn = vi.fn().mockResolvedValue("pending");
        await expect(
            pollUntil({
                fn,
                condition: (v) => v === "done",
                interval: 10,
                timeout: 50,
            }),
        ).rejects.toThrow("Polling timed out");
    });

    it("should propagate errors from fn", async () => {
        const fn = vi.fn().mockRejectedValue(new Error("network error"));
        await expect(
            pollUntil({
                fn,
                condition: () => true,
            }),
        ).rejects.toThrow("network error");
    });

    it("should wait the specified interval between polls", async () => {
        let callCount = 0;
        const fn = vi.fn().mockImplementation(async () => {
            callCount++;
            return callCount >= 2 ? "done" : "pending";
        });
        const start = Date.now();
        await pollUntil({
            fn,
            condition: (v) => v === "done",
            interval: 100,
        });
        const elapsed = Date.now() - start;
        expect(elapsed).toBeGreaterThanOrEqual(80);
        expect(fn).toHaveBeenCalledTimes(2);
    });

    it("should work with complex result types", async () => {
        const fn = vi.fn().mockResolvedValue({ status: "complete", value: 42 });
        const result = await pollUntil({
            fn,
            condition: (r) => r.status === "complete",
        });
        expect(result).toEqual({ status: "complete", value: 42 });
    });
});
