type QueuedAction<T extends (...args: any) => R, R = unknown> = {
    action: T;
    args: Parameters<T> | Parameters<T>[0];
    resolve: (value: R) => void;
    reject: (e: Error) => void;
};

/**
 * This queue waits until the current promise is resolved and only executes the last enqueued
 * promise. Promises added between the last and the currently executing promise are skipped.
 * This is useful when promises earlier enqueued become obsolete.
 * See also: https://stackoverflow.com/questions/53540348/js-async-await-tasks-queue
 */
export class LastQueue<T extends (...args: any) => R, R = unknown> {
    throttlePeriod: number;
    private queuedPromises: Record<string | number, QueuedAction<T, R>> = {};
    private pendingPromise = false;

    constructor(throttlePeriod = 1000) {
        this.throttlePeriod = throttlePeriod;
    }

    async enqueue(action: T, args: Parameters<T> | Parameters<T>[0], key: string | number = 0) {
        return new Promise((resolve, reject) => {
            this.queuedPromises[key] = { action, args, resolve, reject };
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
                let payload;
                const args = item.args;

                if (Array.isArray(args)) {
                    payload = await item.action(...(args as Array<unknown>));
                } else {
                    payload = await item.action(args);
                }

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
