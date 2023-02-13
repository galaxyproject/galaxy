type ParametersOrUnknown<T extends () => any> = Parameters<T> extends never ? unknown[] : Parameters<T>;

type QueuedAction<Action extends (...args: any) => Promise<any>> = {
    action: Action;
    args: ParametersOrUnknown<Action>;
    resolve: (value: Awaited<ReturnType<Action>>) => void;
    reject: (reason?: unknown) => void;
};

/**
 * This queue waits until the current promise is resolved and only executes the last enqueued
 * promise. Promises added between the last and the currently executing promise are skipped.
 * This is useful when promises earlier enqueued become obsolete.
 * See also: https://stackoverflow.com/questions/53540348/js-async-await-tasks-queue
 */
export class LastQueue<Action extends (...args: any[]) => Promise<any>, Key extends number | string = 0> {
    throttlePeriod: number;
    nextPromise: Map<string | number, QueuedAction<Action>>;
    promisePending: boolean;

    constructor(throttlePeriod = 1000) {
        this.throttlePeriod = throttlePeriod;
        this.nextPromise = new Map();
        this.promisePending = false;
    }

    async enqueue(action: Action, args: ParametersOrUnknown<Action>, key: Key = 0 as Key) {
        return new Promise((resolve, reject) => {
            this.nextPromise.set(key, { action, args, resolve, reject });
            this.dequeue();
        });
    }

    async dequeue() {
        if (!this.promisePending && this.nextPromise.size > 0) {
            const [key, item] = this.nextPromise.entries().next().value as [Key, QueuedAction<Action>];
            this.nextPromise.delete(key);
            this.promisePending = true;

            try {
                const payload = (await item.action(...item.args)) as Awaited<ReturnType<Action>>;
                item.resolve(payload);
            } catch (e) {
                item.reject(e);
            } finally {
                setTimeout(() => {
                    this.promisePending = false;
                    this.dequeue();
                }, this.throttlePeriod);
            }
        }
    }
}
