import { describe, expect, it, vi } from "vitest";

import { dedupeInFlight, memoizeUntilRejected, rerunWhileBusy } from "./sharedPromise";

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

describe("rerunWhileBusy", () => {
    it("runs once when called while idle", async () => {
        const task = vi.fn(async () => {});
        const run = rerunWhileBusy(task);
        await run();
        expect(task).toHaveBeenCalledTimes(1);
    });

    it("runs once more after the current run for any calls made while it runs, and all callers wait for it", async () => {
        const first = deferred<void>();
        const second = deferred<void>();
        const task = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
        const run = rerunWhileBusy(task);
        let settled = 0;
        const calls = [run(), run(), run()].map((call) => call.then(() => settled++));
        expect(task).toHaveBeenCalledTimes(1);

        first.resolve();
        await vi.waitFor(() => expect(task).toHaveBeenCalledTimes(2));
        expect(settled).toBe(0);

        second.resolve();
        await Promise.all(calls);
        expect(settled).toBe(3);
        expect(task).toHaveBeenCalledTimes(2);
    });

    it("rejects every waiting caller and runs again on the next call", async () => {
        const first = deferred<void>();
        const task = vi.fn().mockReturnValueOnce(first.promise).mockResolvedValue(undefined);
        const run = rerunWhileBusy(task);
        const waiting = [run(), run()];

        first.reject(new Error("boom"));
        await Promise.all(waiting.map((call) => expect(call).rejects.toThrow("boom")));
        expect(task).toHaveBeenCalledTimes(1);

        await run();
        expect(task).toHaveBeenCalledTimes(2);
    });
});
