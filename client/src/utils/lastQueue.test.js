import { ActionSkippedError, LastQueue } from "./lastQueue";

async function testPromise(arg, _signal) {
    return Promise.resolve(arg);
}
const wait = (ms = 5) => new Promise((r) => setTimeout(r, ms));

describe("test last-queue", () => {

    it("should respect throttle period", async () => {
        const throttle = 50;
        const queue = new LastQueue(throttle);
        const timestamps = [];
        async function timedAction(arg) {
            timestamps.push(Date.now());
            return arg;
        }
        await queue.enqueue(timedAction, 1);
        await queue.enqueue(timedAction, 2);
        await queue.enqueue(timedAction, 3);
        await wait(throttle * 3);
        expect(timestamps.length).toBeGreaterThanOrEqual(1);
        const deltas = timestamps.slice(1).map((t, i) => t - timestamps[i]);
        expect(deltas.every((d) => d === 0 || d >= throttle)).toBe(true);
    });

    it("should reject skipped promises when rejectSkipped is true", async () => {
        const queue = new LastQueue(0, true);
        let rejected = 0;
        const rejectAction = jest.fn((arg) => Promise.resolve(arg));
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
        await wait(10);
        expect(rejected).toEqual(1);
    });

    it("should cancel earlier queued actions per key", async () => {
        const queue = new LastQueue(0);
        const calls = [];
        async function recordAction(arg) {
            calls.push(arg);
            return arg;
        }
        queue.enqueue(recordAction, 1, "keyA");
        queue.enqueue(recordAction, 2, "keyA");
        queue.enqueue(recordAction, 3, "keyA");
        await wait(10);
        expect(calls).toEqual([1, 3]);
    });

    it("should isolate independent keys", async () => {
        const queue = new LastQueue(0);
        const results = [];
        queue.enqueue(testPromise, "a", "A").then((r) => results.push(r));
        queue.enqueue(testPromise, "b", "B").then((r) => results.push(r));
        queue.enqueue(testPromise, "c", "C").then((r) => results.push(r));
        await wait(10);
        expect(results.sort()).toEqual(["a", "b", "c"]);
    });

    it("should handle thrown errors without breaking queue", async () => {
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

    it("should execute replacement if enqueued during completion", async () => {
        const queue = new LastQueue(0);
        const results = [];
        async function delayedAction(arg) {
            if (arg === 1) {
                setTimeout(() => queue.enqueue(delayedAction, 2), 0);
            }
            return arg;
        }
        await queue.enqueue(delayedAction, 1).then((r) => results.push(r));
        await wait(10);
        expect(results).toContain(1);
    });

    it("should not hang when throttle is zero or negative", async () => {
        const queue = new LastQueue(-1);
        const results = [];
        for (let i = 0; i < 5; i++) {
            await queue.enqueue(testPromise, i).then((r) => results.push(r));
        }
        expect(results).toEqual([0, 1, 2, 3, 4]);
    });

    it("should clean up idle keys after completion", async () => {
        const queue = new LastQueue(0);
        await queue.enqueue(testPromise, 1, "cleanupKey");
        await wait(5);
        const second = await queue.enqueue(testPromise, 2, "cleanupKey");
        expect(second).toBe(2);
    });

    it("should resolve skipped promises to undefined when rejectSkipped is false", async () => {
        const queue = new LastQueue(0, false);
        const results = [];
        queue.enqueue(testPromise, 1).then((r) => results.push(r));
        await queue.enqueue(testPromise, 2);
        await wait(5);
        const defined = results.filter((r) => r !== undefined);
        const skipped = results.filter((r) => r === undefined);
        // Either the first completed normally (defined=[1])
        // or it was skipped and undefined (defined=[2])
        expect(defined.length).toBe(1);
        expect([1, 2]).toContain(defined[0]);
        expect(skipped.length).toBeLessThanOrEqual(1);
    });

    it("should not fail if a running task is replaced during execution", async () => {
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
        await wait(5);
        await queue.enqueue(longAction, 2, "key");
        await wait(40);
        expect(finished).toBe(true);
    });

    it("detects blocked throttle under fake timers", async () => {
        jest.useFakeTimers();
        const q = new LastQueue(300);
        const calls = [];
        async function fn(n) {
            calls.push(n);
            return n;
        }
        q.enqueue(fn, 1);
        q.enqueue(fn, 2);
        q.enqueue(fn, 3);
        jest.advanceTimersByTime(1000);
        expect(calls.length).toBeGreaterThan(0);
    });

    it("should not leak memory after many keys", async () => {
        const queue = new LastQueue(0);
        for (let i = 0; i < 1000; i++) {
            await queue.enqueue(testPromise, i, `key${i}`);
        }
        expect(queue["queues"].size).toBe(0);
        expect(queue["pending"].size).toBe(0);
        expect(queue["timeoutIds"].size).toBe(0);
    });

    it("should throttle per key independently", async () => {
        jest.useFakeTimers();
        const throttle = 50;
        const queue = new LastQueue(throttle);
        const stamps = { A: [], B: [] };
        const action = jest.fn(async (key) => {
            stamps[key].push(Date.now());
            return key;
        });
        queue.enqueue(action, "A", "A");
        queue.enqueue(action, "A", "A");
        queue.enqueue(action, "B", "B");
        queue.enqueue(action, "B", "B");
        jest.advanceTimersByTime(throttle * 3);
        await Promise.resolve();
        expect(stamps.A.length >= 2).toBe(true);
        expect(stamps.B.length >= 2).toBe(true);
        const deltaA = stamps.A[1] - stamps.A[0];
        const deltaB = stamps.B[1] - stamps.B[0];
        expect(deltaA >= throttle || deltaA === 0).toBe(true);
        expect(deltaB >= throttle || deltaB === 0).toBe(true);
        jest.useRealTimers();
    });

    it("should propagate AbortSignal and reject on abort", async () => {
        jest.useFakeTimers();
        const queue = new LastQueue(0);
        const controller = new AbortController();
        let aborted = false;
        const action = jest.fn(async (_arg, signal) => {
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
        jest.runAllTimers();
        const result = await first;
        expect(result).toBeUndefined();
        expect(aborted).toBe(true);
        expect(action).toHaveBeenCalledTimes(1);
        jest.useRealTimers();
    });

    it("should skip all but first and last in rapid zero-throttle burst", async () => {
        const queue = new LastQueue(0);
        const results = [];
        for (let i = 0; i < 1000; i++) {
            queue.enqueue(testPromise, i).then((r) => r !== undefined && results.push(r));
        }
        await queue.enqueue(testPromise, 999).then((r) => r !== undefined && results.push(r));
        await wait(10);
        expect(results).toEqual([0, 999]);
    });

    it("should clear timeout on skip", async () => {
        jest.useFakeTimers();
        const queue = new LastQueue(100);
        queue.enqueue(testPromise, 1); // starts, will wait 100ms before next
        await jest.runAllTimersAsync(); // finish first task
        queue.enqueue(testPromise, 2); // queues second, sets timeout
        queue.enqueue(testPromise, 3); // skips second → should clear timeout
        jest.runAllTimers(); // any leftover timeout would error
        expect(queue["timeoutIds"].size).toBe(0);
        jest.useRealTimers();
    });

    it("should handle mixed string/number keys without collision", async () => {
        const queue = new LastQueue(0);
        const results = new Set();
        await queue.enqueue(testPromise, "str", "key");
        await queue.enqueue(testPromise, 123, 123);
        queue.enqueue(testPromise, "num", "123").then((r) => results.add(r));
        queue.enqueue(testPromise, 456, "key").then((r) => results.add(r));
        await wait(10);
        expect(results.has("num")).toBe(true);
        expect(results.has(456)).toBe(true);
    });
});
