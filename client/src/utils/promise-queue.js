/**
 * This queue waits until the current promise is resolved and only executes the last enqueued
 * promise. Promises added between the last and the currently executing promise are skipped.
 * This is useful when promises earlier enqueued become obsolete.
 * See also: https://stackoverflow.com/questions/53540348/js-async-await-tasks-queue
 */
export class LastQueue {
    constructor(throttlePeriod = 1000) {
        this.throttlePeriod = throttlePeriod;
        this.nextPromise = {};
        this.pendingPromise = false;
    }

    async enqueue(action, args, key = 0) {
        return new Promise((resolve, reject) => {
            this.nextPromise[key] = { action, args, resolve, reject };
            this.dequeue();
        });
    }

    async dequeue() {
        const keys = Object.keys(this.nextPromise);
        if (!this.pendingPromise && keys.length > 0) {
            const nextKey = keys[0];
            const item = this.nextPromise[nextKey];
            delete this.nextPromise[nextKey];
            this.pendingPromise = true;
            try {
                const payload = await item.action(item.args);
                item.resolve(payload);
            } catch (e) {
                item.reject(e);
            } finally {
                setTimeout(() => {
                    this.pendingPromise = false;
                    this.dequeue();
                }, this.throttlePeriod);
            }
        }
    }
}
