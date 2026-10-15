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

/**
 * Run `fn` one call at a time. Calls made while it runs make it run once more afterwards, so the
 * last call always sees the latest state; they share the promise of that run.
 * A rejection is shared with callers already waiting; the next call runs `fn` again.
 */
export function rerunWhileBusy(fn: () => Promise<void>): () => Promise<void> {
    let running: Promise<void> | undefined;
    let rerun = false;
    return () => {
        if (running) {
            rerun = true;
        } else {
            running = (async () => {
                do {
                    rerun = false;
                    await callAsync(fn);
                } while (rerun);
            })().finally(() => {
                running = undefined;
            });
        }
        return running;
    };
}
