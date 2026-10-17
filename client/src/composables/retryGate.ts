import { del, ref, set } from "vue";

import { ApiError, isRetryableApiError, MAX_RETRIES, RETRY_BACKOFF_CAP_MS, retryBackoffMs } from "@/utils/simple-error";

function retryAfterMsOf(error: Error): number | undefined {
    return error instanceof ApiError ? error.retryAfterMs : undefined;
}

/**
 * Per-id retry bookkeeping for lazily fetched items: counts failures, and after a
 * retryable error blocks refetching for a jittered exponential backoff
 * (at most ``MAX_RETRIES`` retries). A ``Retry-After`` longer than
 * ``RETRY_BACKOFF_CAP_MS`` makes the error final. State is reactive, so getters gated on
 * ``canRetry`` re-evaluate and refetch when a backoff elapses.
 *
 * @param isRetryable Returns true for errors worth retrying.
 */
export function useRetryGate(isRetryable: (error: Error) => boolean = isRetryableApiError) {
    const retryCounts = ref<{ [key: string]: number }>({});
    /** Ids waiting out a backoff; cleared by timer. */
    const retryPending = ref<{ [key: string]: boolean }>({});
    const retryTimers: { [key: string]: ReturnType<typeof setTimeout> } = {};

    /** True while ``error`` is not final: a retry is pending or in flight. */
    function isRetrying(id: string, error: Error): boolean {
        const retryAfterMs = retryAfterMsOf(error);
        if (retryAfterMs !== undefined && retryAfterMs > RETRY_BACKOFF_CAP_MS) {
            return false;
        }
        return isRetryable(error) && (retryCounts.value[id] ?? 0) <= MAX_RETRIES;
    }

    /** True while ``id`` is waiting out a backoff. */
    function isRetryPending(id: string): boolean {
        return Boolean(retryPending.value[id]);
    }

    /** True if an item that failed with ``error`` may be fetched again now. */
    function canRetry(id: string, error: Error): boolean {
        return isRetrying(id, error) && !isRetryPending(id);
    }

    /**
     * ``error`` once final, null while its retry is pending or in flight.
     * An error never passed to ``recordFailure`` is final.
     */
    function finalError<E extends Error>(id: string, error: E | null | undefined): E | null {
        if (!error) {
            return null;
        }
        return retryCounts.value[id] !== undefined && isRetrying(id, error) ? null : error;
    }

    function clearRetry(id: string) {
        clearTimeout(retryTimers[id]);
        delete retryTimers[id];
        del(retryPending.value, id);
    }

    function recordFailure(id: string, error: Error) {
        const attempt = (retryCounts.value[id] ?? 0) + 1;
        set(retryCounts.value, id, attempt);
        if (isRetrying(id, error)) {
            clearTimeout(retryTimers[id]);
            set(retryPending.value, id, true);
            const retryAfterMs = retryAfterMsOf(error);
            retryTimers[id] = setTimeout(
                () => {
                    delete retryTimers[id];
                    del(retryPending.value, id);
                },
                retryBackoffMs(attempt, retryAfterMs),
            );
        } else {
            clearRetry(id);
        }
    }

    function recordSuccess(id: string) {
        del(retryCounts.value, id);
        clearRetry(id);
    }

    return { canRetry, finalError, isRetrying, isRetryPending, recordFailure, recordSuccess };
}
