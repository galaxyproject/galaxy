import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { pollUntil } from "./pollUntil";

describe("pollUntil", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
    });

    it("returns immediately when the first result satisfies the condition", async () => {
        const fn = vi.fn<() => Promise<string>>().mockResolvedValue("done");

        const result = await pollUntil({ fn, condition: (value) => value === "done" });

        expect(result).toBe("done");
        expect(fn).toHaveBeenCalledTimes(1);
        expect(vi.getTimerCount()).toBe(0);
    });

    it("returns the third result after two pending polls", async () => {
        const fn = vi
            .fn<() => Promise<string>>()
            .mockResolvedValueOnce("pending")
            .mockResolvedValueOnce("pending")
            .mockResolvedValue("ready");

        const polling = pollUntil({ fn, condition: (value) => value === "ready", interval: 10 });
        await vi.advanceTimersByTimeAsync(20);

        expect(await polling).toBe("ready");
        expect(fn).toHaveBeenCalledTimes(3);
    });

    it("rejects when no result satisfies the condition before the 50ms timeout", async () => {
        const fn = vi.fn<() => Promise<string>>().mockResolvedValue("pending");
        const polling = pollUntil({ fn, condition: (value) => value === "done", interval: 10, timeout: 50 });
        const rejection = expect(polling).rejects.toThrow("Polling timed out");

        await vi.advanceTimersByTimeAsync(50);

        await rejection;
        expect(fn).toHaveBeenCalledTimes(5);
        expect(vi.getTimerCount()).toBe(0);
    });

    it("propagates a rejected poll without scheduling a retry", async () => {
        const fn = vi.fn<() => Promise<string>>().mockRejectedValue(new Error("network error"));

        await expect(pollUntil({ fn, condition: () => true })).rejects.toThrow("network error");

        expect(fn).toHaveBeenCalledTimes(1);
        expect(vi.getTimerCount()).toBe(0);
    });

    it("waits the full 100ms interval before polling again", async () => {
        const fn = vi.fn<() => Promise<string>>().mockResolvedValueOnce("pending").mockResolvedValue("done");
        const polling = pollUntil({ fn, condition: (value) => value === "done", interval: 100 });

        await vi.advanceTimersByTimeAsync(99);
        expect(fn).toHaveBeenCalledTimes(1);

        await vi.advanceTimersByTimeAsync(1);

        expect(await polling).toBe("done");
        expect(fn).toHaveBeenCalledTimes(2);
    });

    it("returns the complete object that satisfies the condition", async () => {
        const fn = vi
            .fn<() => Promise<{ status: string; value: number }>>()
            .mockResolvedValue({ status: "complete", value: 42 });

        const result = await pollUntil({ fn, condition: (value) => value.status === "complete" });

        expect(result).toEqual({ status: "complete", value: 42 });
    });
});
