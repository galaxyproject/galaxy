/** Call `fn`, turning a synchronous throw into a rejected promise. */
function callAsync<T>(fn: () => Promise<T>): Promise<T> {
    try {
        return fn();
    } catch (error) {
        return Promise.reject(error);
    }
}

/**
 * Call `fn` once and share its promise with concurrent and later callers.
 * A rejection is shared with callers already waiting, then forgotten so the next call retries.
 */
export function memoizeUntilRejected<T>(fn: () => Promise<T>): () => Promise<T> {
    let promise: Promise<T> | undefined;
    return () => {
        if (!promise) {
            promise = callAsync(fn).catch((error) => {
                promise = undefined;
                throw error;
            });
        }
        return promise;
    };
}

/**
 * Share one in-flight call of `fn` per key between concurrent callers.
 * Once it settles (resolved or rejected) the next call for that key calls `fn` again.
 */
export function dedupeInFlight<K, T>(fn: (key: K) => Promise<T>): (key: K) => Promise<T> {
    const inFlight = new Map<K, Promise<T>>();
    return (key: K) => {
        let promise = inFlight.get(key);
        if (!promise) {
            promise = callAsync(() => fn(key)).finally(() => inFlight.delete(key));
            inFlight.set(key, promise);
        }
        return promise;
    };
}
