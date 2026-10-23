import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed } from "vue";

import { ApiError, MAX_RETRIES, RETRY_BACKOFF_BASE_MS, RETRY_BACKOFF_CAP_MS } from "@/utils/simple-error";

import { useRetryGate } from "./retryGate";

const ID = "item-1";

/** Backoff for a 1-based attempt with ``Math.random`` mocked to 0. */
function minDelay(attempt: number) {
    return (RETRY_BACKOFF_BASE_MS * 2 ** (attempt - 1)) / 2;
}

describe("useRetryGate", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.spyOn(Math, "random").mockReturnValue(0);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    it("blocks a retry until the backoff elapses", () => {
        const gate = useRetryGate();
        const error = new ApiError("Too Many Requests", 429);

        gate.recordFailure(ID, error);
        expect(gate.canRetry(ID, error)).toBe(false);
        expect(gate.isRetrying(ID, error)).toBe(true);
        expect(gate.isRetryPending(ID)).toBe(true);

        vi.advanceTimersByTime(minDelay(1) - 1);
        expect(gate.canRetry(ID, error)).toBe(false);
        vi.advanceTimersByTime(1);
        expect(gate.canRetry(ID, error)).toBe(true);
        expect(gate.isRetryPending(ID)).toBe(false);
    });

    it("grows the backoff and gives up after MAX_RETRIES retries", () => {
        const gate = useRetryGate();
        const error = new ApiError("Service Unavailable", 503);

        for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
            gate.recordFailure(ID, error);
            vi.advanceTimersByTime(minDelay(attempt) - 1);
            expect(gate.canRetry(ID, error)).toBe(false);
            vi.advanceTimersByTime(1);
            expect(gate.canRetry(ID, error)).toBe(true);
        }
        gate.recordFailure(ID, error);
        expect(gate.canRetry(ID, error)).toBe(false);
        expect(gate.isRetrying(ID, error)).toBe(false);
        expect(gate.isRetryPending(ID)).toBe(false);
    });

    it("waits at least Retry-After", () => {
        const gate = useRetryGate();
        const error = new ApiError("Too Many Requests", 429);
        error.retryAfterMs = 10_000;

        gate.recordFailure(ID, error);
        vi.advanceTimersByTime(9_999);
        expect(gate.canRetry(ID, error)).toBe(false);
        vi.advanceTimersByTime(1);
        expect(gate.canRetry(ID, error)).toBe(true);
    });

    it("gives up when Retry-After exceeds the backoff cap", () => {
        const gate = useRetryGate();
        const error = new ApiError("Too Many Requests", 429);
        error.retryAfterMs = RETRY_BACKOFF_CAP_MS + 1000;

        gate.recordFailure(ID, error);
        expect(gate.canRetry(ID, error)).toBe(false);
        expect(gate.isRetrying(ID, error)).toBe(false);
        expect(gate.isRetryPending(ID)).toBe(false);
        expect(gate.finalError(ID, error)).toBe(error);
    });

    it("retries when Retry-After equals the backoff cap", () => {
        const gate = useRetryGate();
        const error = new ApiError("Too Many Requests", 429);
        error.retryAfterMs = RETRY_BACKOFF_CAP_MS;

        gate.recordFailure(ID, error);
        expect(gate.finalError(ID, error)).toBeNull();
        vi.advanceTimersByTime(RETRY_BACKOFF_CAP_MS);
        expect(gate.canRetry(ID, error)).toBe(true);
    });

    it("never retries a non-retryable error", () => {
        const gate = useRetryGate();
        const error = new ApiError("Forbidden", 403);

        gate.recordFailure(ID, error);
        expect(gate.canRetry(ID, error)).toBe(false);
        expect(gate.isRetrying(ID, error)).toBe(false);
        expect(gate.isRetryPending(ID)).toBe(false);
    });

    it("uses the given retryable predicate", () => {
        const gate = useRetryGate(() => true);
        const error = new Error("Network Error");

        gate.recordFailure(ID, error);
        expect(gate.isRetrying(ID, error)).toBe(true);
        vi.advanceTimersByTime(minDelay(1));
        expect(gate.canRetry(ID, error)).toBe(true);
    });

    it("restarts the backoff on a repeated failure and resets on success", () => {
        const gate = useRetryGate();
        const error = new ApiError("Too Many Requests", 429);

        gate.recordFailure(ID, error);
        vi.advanceTimersByTime(minDelay(1) - 1);
        // A failure during the backoff replaces it with the next, longer one.
        gate.recordFailure(ID, error);
        vi.advanceTimersByTime(minDelay(2) - 1);
        expect(gate.isRetryPending(ID)).toBe(true);
        vi.advanceTimersByTime(1);
        expect(gate.isRetryPending(ID)).toBe(false);

        gate.recordFailure(ID, error);
        gate.recordSuccess(ID);
        expect(gate.isRetryPending(ID)).toBe(false);
        // Count is reset: a later failure starts from the first backoff again.
        gate.recordFailure(ID, error);
        vi.advanceTimersByTime(minDelay(1));
        expect(gate.canRetry(ID, error)).toBe(true);
    });

    it("hides a retryable error until retries are exhausted", () => {
        const gate = useRetryGate();
        const error = new ApiError("Service Unavailable", 503);

        for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
            gate.recordFailure(ID, error);
            expect(gate.finalError(ID, error)).toBeNull();
            // Backoff elapsed, retry in flight.
            vi.advanceTimersByTime(minDelay(attempt));
            expect(gate.finalError(ID, error)).toBeNull();
        }
        gate.recordFailure(ID, error);
        expect(gate.finalError(ID, error)).toBe(error);
    });

    it("returns a non-retryable error immediately", () => {
        const gate = useRetryGate();
        const error = new ApiError("Not Found", 404);

        gate.recordFailure(ID, error);
        expect(gate.finalError(ID, error)).toBe(error);
    });

    it("treats an error never recorded as a failure as final", () => {
        const gate = useRetryGate();
        const error = new ApiError("Service Unavailable", 503);

        expect(gate.finalError(ID, error)).toBe(error);
        expect(gate.finalError(ID, undefined)).toBeNull();
    });

    it("re-evaluates dependent computeds when the backoff elapses or retries run out", () => {
        const gate = useRetryGate();
        const error = new ApiError("Too Many Requests", 429);
        const canRetry = computed(() => gate.canRetry(ID, error));
        const isRetrying = computed(() => gate.isRetrying(ID, error));

        gate.recordFailure(ID, error);
        expect(canRetry.value).toBe(false);
        vi.advanceTimersByTime(minDelay(1));
        expect(canRetry.value).toBe(true);

        for (let attempt = 2; attempt <= MAX_RETRIES; attempt++) {
            gate.recordFailure(ID, error);
        }
        expect(isRetrying.value).toBe(true);
        gate.recordFailure(ID, error);
        expect(isRetrying.value).toBe(false);
    });
});
