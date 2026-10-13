import { describe, expect, it, vi } from "vitest";

import { dedupeInFlight, memoizeUntilRejected } from "./sharedPromise";

/** A promise whose settlement the test controls. */
function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (error: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return { promise, resolve, reject };
}

describe("memoizeUntilRejected", () => {
    it("shares one call between concurrent callers", async () => {
        const request = vi.fn(async () => "value");
        const load = memoizeUntilRejected(request);
        const results = await Promise.all([load(), load(), load()]);
        expect(results).toEqual(["value", "value", "value"]);
        expect(request).toHaveBeenCalledTimes(1);
    });

    it("keeps the resolved result for later callers", async () => {
        const request = vi.fn(async () => "value");
        const load = memoizeUntilRejected(request);
        await load();
        expect(await load()).toBe("value");
        expect(request).toHaveBeenCalledTimes(1);
    });

    it("rejects all concurrent callers, then retries on the next call", async () => {
        const request = vi.fn().mockRejectedValueOnce(new Error("boom")).mockResolvedValueOnce("value");
        const load = memoizeUntilRejected(request);
        const results = await Promise.allSettled([load(), load()]);
        expect(results.map((result) => result.status)).toEqual(["rejected", "rejected"]);
        expect(request).toHaveBeenCalledTimes(1);

        expect(await load()).toBe("value");
        expect(request).toHaveBeenCalledTimes(2);
    });

    it("turns a synchronous throw into a rejection that is not kept", async () => {
        const request = vi.fn((): Promise<string> => {
            throw new Error("boom");
        });
        const load = memoizeUntilRejected(request);
        await expect(load()).rejects.toThrow("boom");
        await expect(load()).rejects.toThrow("boom");
        expect(request).toHaveBeenCalledTimes(2);
    });
});

describe("dedupeInFlight", () => {
    it("shares one call per key between concurrent callers", async () => {
        const pending = deferred<string>();
        const request = vi.fn(() => pending.promise);
        const fetch = dedupeInFlight(request);
        const calls = [fetch("a"), fetch("a"), fetch("a")];
        expect(request).toHaveBeenCalledTimes(1);
        pending.resolve("value");
        expect(await Promise.all(calls)).toEqual(["value", "value", "value"]);
    });

    it("isolates keys", async () => {
        const request = vi.fn(async (key: string) => `value-${key}`);
        const fetch = dedupeInFlight(request);
        expect(await Promise.all([fetch("a"), fetch("b"), fetch("a")])).toEqual(["value-a", "value-b", "value-a"]);
        expect(request).toHaveBeenCalledTimes(2);
        expect(request).toHaveBeenNthCalledWith(1, "a");
        expect(request).toHaveBeenNthCalledWith(2, "b");
    });

    it("calls again once the previous call has resolved", async () => {
        const request = vi.fn(async (key: string) => `value-${key}`);
        const fetch = dedupeInFlight(request);
        await fetch("a");
        await fetch("a");
        expect(request).toHaveBeenCalledTimes(2);
    });

    it("rejects all concurrent callers, then retries on the next call", async () => {
        const request = vi.fn().mockRejectedValueOnce(new Error("boom")).mockResolvedValueOnce("value");
        const fetch = dedupeInFlight(request);
        const results = await Promise.allSettled([fetch("a"), fetch("a")]);
        expect(results.map((result) => result.status)).toEqual(["rejected", "rejected"]);
        expect(request).toHaveBeenCalledTimes(1);

        expect(await fetch("a")).toBe("value");
        expect(request).toHaveBeenCalledTimes(2);
    });

    it("turns a synchronous throw into a rejection that is not kept", async () => {
        const request = vi.fn((_key: string): Promise<string> => {
            throw new Error("boom");
        });
        const fetch = dedupeInFlight(request);
        await expect(fetch("a")).rejects.toThrow("boom");
        await expect(fetch("a")).rejects.toThrow("boom");
        expect(request).toHaveBeenCalledTimes(2);
    });
});
