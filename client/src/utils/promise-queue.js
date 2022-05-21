/**
 * This queue waits until the current promise is resolved and only executes the last enqueued
 * promise. Promises added between the last and the currently executing promise are skipped.
 * This is useful when promises earlier enqueued become obsolete.
 * See also: https://stackoverflow.com/questions/53540348/js-async-await-tasks-queue
 */
export class LastQueue {
    constructor(throttlePeriod = 1000) {
        this.throttlePeriod = throttlePeriod;
        this.nextPromise = null;
        this.pendingPromise = false;
    }

    async enqueue(action, args) {
        return new Promise((resolve, reject) => {
            this.nextPromise = { action, args, resolve, reject };
            this.dequeue();
        });
    }

    async dequeue() {
        if (!this.pendingPromise && this.nextPromise) {
            const item = this.nextPromise;
            this.nextPromise = null;
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
