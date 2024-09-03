type QueuedAction<T extends (...args: any) => R, R = ReturnType<T>> = {
    action: T;
    arg: Parameters<T>[0];
    resolve: (value: R) => void;
    reject: (e: Error) => void;
};

export class ActionSkippedError extends Error {}

/**
 * This queue waits until the current promise is resolved and only executes the last enqueued
 * promise. Promises added between the last and the currently executing promise are skipped.
 * This is useful when promises earlier enqueued become obsolete.
 * See also: https://stackoverflow.com/questions/53540348/js-async-await-tasks-queue
 */
export class LastQueue<T extends (arg: any) => R, R = ReturnType<T>> {
    throttlePeriod: number;
    /** Throw an error if a queued action is skipped. This avoids dangling promises */
    rejectSkipped: boolean;
    private queuedPromises: Record<string | number, QueuedAction<T, R>> = {};
    private pendingPromise = false;

    constructor(throttlePeriod = 1000, rejectSkipped = false) {
        this.throttlePeriod = throttlePeriod;
        this.rejectSkipped = rejectSkipped;
    }

    private skipPromise(key: string | number) {
        if (!this.rejectSkipped) {
            return;
        }

        const promise = this.queuedPromises[key];
        promise?.reject(new ActionSkippedError());
    }

    async enqueue(action: T, arg: Parameters<T>[0], key: string | number = 0): Promise<R> {
        return new Promise((resolve, reject) => {
            this.skipPromise(key);
            this.queuedPromises[key] = { action, arg, resolve, reject };
            this.dequeue();
        });
    }

    async dequeue() {
        const keys = Object.keys(this.queuedPromises);
        if (!this.pendingPromise && keys.length > 0) {
            const nextKey = keys[0] as string;
            const item = this.queuedPromises[nextKey] as QueuedAction<T, R>;
            delete this.queuedPromises[nextKey];
            this.pendingPromise = true;

            try {
                const payload = await item.action(item.arg);
                item.resolve(payload);
            } catch (e) {
                item.reject(e as Error);
            } finally {
                setTimeout(() => {
                    this.pendingPromise = false;
                    this.dequeue();
                }, this.throttlePeriod);
            }
        }
    }
}
