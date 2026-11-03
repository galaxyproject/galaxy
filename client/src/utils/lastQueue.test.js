import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ActionSkippedError, LastQueue } from "./lastQueue";

async function returnArgument(arg) {
    return arg;
}

describe("LastQueue", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(0);
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
    });

    it("waits one throttle period before running the latest pending action", async () => {
        const throttle = 50;
        const queue = new LastQueue(throttle);
        const timestamps = [];
        async function timedAction(arg) {
            timestamps.push(Date.now());
            return arg;
        }
        queue.enqueue(timedAction, 1);
        queue.enqueue(timedAction, 2);
        queue.enqueue(timedAction, 3);
        await vi.advanceTimersByTimeAsync(throttle * 3);
        expect(timestamps).toEqual([0, throttle]);
    });

    it("rejects the superseded pending action with ActionSkippedError", async () => {
        const queue = new LastQueue(0, true);
        let rejected = 0;
        const rejectAction = vi.fn((arg) => Promise.resolve(arg));
        queue.enqueue(rejectAction, 1).catch((e) => {
            if (e instanceof ActionSkippedError) {
                rejected++;
            }
        });
        queue.enqueue(rejectAction, 2).catch((e) => {
            if (e instanceof ActionSkippedError) {
                rejected++;
            }
        });
        await queue.enqueue(rejectAction, 3);
        await vi.advanceTimersByTimeAsync(10);
        expect(rejected).toEqual(1);
    });

    it("runs the first and latest actions for the same key", async () => {
        const queue = new LastQueue(0);
        const calls = [];
        async function recordAction(arg) {
            calls.push(arg);
            return arg;
        }
        queue.enqueue(recordAction, 1, "keyA");
        queue.enqueue(recordAction, 2, "keyA");
        queue.enqueue(recordAction, 3, "keyA");
        await vi.advanceTimersByTimeAsync(10);
        expect(calls).toEqual([1, 3]);
    });

    it("resolves actions for three independent keys", async () => {
        const queue = new LastQueue(0);
        const results = [];
        queue.enqueue(returnArgument, "a", "A").then((r) => results.push(r));
        queue.enqueue(returnArgument, "b", "B").then((r) => results.push(r));
        queue.enqueue(returnArgument, "c", "C").then((r) => results.push(r));
        await vi.advanceTimersByTimeAsync(10);
        expect(results.sort()).toEqual(["a", "b", "c"]);
    });

    it("runs the next action after the first throws", async () => {
        const queue = new LastQueue(0);
        const results = [];
        async function faultyAction(arg) {
            if (arg === 1) {
                throw new Error("TestError");
            }
            return arg;
        }
        queue.enqueue(faultyAction, 1).catch((e) => results.push(e.message));
        await queue.enqueue(faultyAction, 2).then((r) => results.push(r));
        expect(results).toContain("TestError");
        expect(results).toContain(2);
    });

    it("runs an action enqueued by the completing action", async () => {
        const queue = new LastQueue(0);
        const results = [];
        const calls = [];
        async function delayedAction(arg) {
            calls.push(arg);
            if (arg === 1) {
                setTimeout(() => queue.enqueue(delayedAction, 2), 0);
            }
            return arg;
        }
        await queue.enqueue(delayedAction, 1).then((r) => results.push(r));
        await vi.advanceTimersByTimeAsync(10);
        expect(results).toContain(1);
        expect(calls).toEqual([1, 2]);
    });

    it("resolves sequential actions with a negative throttle", async () => {
        const queue = new LastQueue(-1);
        const results = [];
        for (let i = 0; i < 5; i++) {
            await queue.enqueue(returnArgument, i).then((r) => results.push(r));
        }
        expect(results).toEqual([0, 1, 2, 3, 4]);
    });

    it("accepts another action on an idle key", async () => {
        const queue = new LastQueue(0);
        await queue.enqueue(returnArgument, 1, "cleanupKey");
        await vi.advanceTimersByTimeAsync(5);
        const second = await queue.enqueue(returnArgument, 2, "cleanupKey");
        expect(second).toBe(2);
    });

    it("preserves the running action when another action is queued", async () => {
        const queue = new LastQueue(0, false);
        const results = [];
        queue.enqueue(returnArgument, 1).then((r) => results.push(r));
        await queue.enqueue(returnArgument, 2);
        await vi.advanceTimersByTimeAsync(5);
        expect(results).toEqual([1]);
    });

    it("resolves a superseded pending action to undefined when rejection is disabled", async () => {
        const queue = new LastQueue(0, false);
        const first = queue.enqueue(returnArgument, 1);
        const skipped = queue.enqueue(returnArgument, 2);
        const latest = queue.enqueue(returnArgument, 3);

        expect(await Promise.all([first, skipped, latest])).toEqual([1, undefined, 3]);
    });

    it("finishes the next action when another action is still running", async () => {
        const queue = new LastQueue(0);
        let finished = false;
        async function longAction(arg, signal) {
            await new Promise((r) => setTimeout(r, 30));
            if (!signal.aborted) {
                finished = true;
            }
            return arg;
        }
        queue.enqueue(longAction, 1, "key");
        await vi.advanceTimersByTimeAsync(5);
        const replacement = queue.enqueue(longAction, 2, "key");
        await vi.runAllTimersAsync();
        await replacement;
        await vi.advanceTimersByTimeAsync(40);
        expect(finished).toBe(true);
    });

    it("starts the first action before the timer queue is advanced", async () => {
        const queue = new LastQueue(300);
        const calls = [];
        async function recordAction(n) {
            calls.push(n);
            return n;
        }
        queue.enqueue(recordAction, 1);
        queue.enqueue(recordAction, 2);
        queue.enqueue(recordAction, 3);
        expect(calls).toEqual([1]);
        vi.advanceTimersByTime(1000);
        expect(calls.length).toBeGreaterThan(0);
        await vi.runAllTimersAsync();
    });

    it("clears queued actions, pending keys, and timeout IDs after 1000 independent keys", async () => {
        const queue = new LastQueue(0);
        for (let i = 0; i < 1000; i++) {
            await queue.enqueue(returnArgument, i, `key${i}`);
        }
        expect(queue["queues"].size).toBe(0);
        expect(queue["pending"].size).toBe(0);
        expect(queue["timeoutIds"].size).toBe(0);
    });

    it("applies the throttle separately to each key", async () => {
        const throttle = 50;
        const queue = new LastQueue(throttle);
        const stamps = { A: [], B: [] };
        const action = vi.fn(async (key) => {
            stamps[key].push(Date.now());
            return key;
        });
        queue.enqueue(action, "A", "A");
        queue.enqueue(action, "A", "A");
        queue.enqueue(action, "B", "B");
        queue.enqueue(action, "B", "B");
        await vi.advanceTimersByTimeAsync(throttle * 3);
        expect(stamps.A).toEqual([0, throttle]);
        expect(stamps.B).toEqual([0, throttle]);
    });

    it("forwards an external abort and resolves the running action to undefined", async () => {
        const queue = new LastQueue(0);
        const controller = new AbortController();
        let aborted = false;
        const action = vi.fn(async (_arg, signal) => {
            signal?.addEventListener("abort", () => {
                aborted = true;
            });
            if (signal?.aborted) {
                throw new Error("Aborted early");
            }
            return "done";
        });
        const first = queue.enqueue(action, null, "key", { signal: controller.signal });
        controller.abort();
        vi.runAllTimers();
        const result = await first;
        expect(result).toBeUndefined();
        expect(aborted).toBe(true);
        expect(action).toHaveBeenCalledTimes(1);
    });

    it("runs only the first and last actions in a 1000-action burst", async () => {
        const queue = new LastQueue(0);
        const results = [];
        for (let i = 0; i < 1000; i++) {
            queue.enqueue(returnArgument, i).then((r) => r !== undefined && results.push(r));
        }
        await queue.enqueue(returnArgument, 999).then((r) => r !== undefined && results.push(r));
        await vi.advanceTimersByTimeAsync(10);
        expect(results).toEqual([0, 999]);
    });

    it("removes the throttle timeout after the latest pending action completes", async () => {
        const queue = new LastQueue(100);
        queue.enqueue(returnArgument, 1);
        await vi.runAllTimersAsync();
        queue.enqueue(returnArgument, 2);
        queue.enqueue(returnArgument, 3);
        vi.runAllTimers();
        expect(queue["timeoutIds"].size).toBe(0);

        await vi.runAllTimersAsync();
        expect(queue["timeoutIds"].size).toBe(0);
    });

    it("runs actions with string and numeric keys", async () => {
        const queue = new LastQueue(0);
        const results = new Set();
        await queue.enqueue(returnArgument, "str", "key");
        await queue.enqueue(returnArgument, 123, 123);
        queue.enqueue(returnArgument, "num", "123").then((r) => results.add(r));
        queue.enqueue(returnArgument, 456, "key").then((r) => results.add(r));
        await vi.advanceTimersByTimeAsync(10);
        expect(results.has("num")).toBe(true);
        expect(results.has(456)).toBe(true);
    });
});
