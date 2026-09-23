/**
 * Polls an async function until a condition is met or timeout is reached.
 * Returns the final result that satisfied the condition.
 *
 * @param fn - Async function to call on each poll iteration.
 * @param condition - Predicate that determines when polling should stop.
 * @param interval - Milliseconds between poll attempts (default: 1000).
 * @param timeout - Maximum milliseconds before throwing a timeout error (default: 600000).
 */
export async function pollUntil<T>({
    fn,
    condition,
    interval = 1000,
    timeout = 600000,
}: {
    fn: () => Promise<T>;
    condition: (result: T) => boolean;
    interval?: number;
    timeout?: number;
}): Promise<T> {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
        const result = await fn();
        if (condition(result)) {
            return result;
        }
        await new Promise((resolve) => setTimeout(resolve, interval));
    }
    throw new Error("Polling timed out");
}
