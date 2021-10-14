/**
 * This queue waits until the current promise is resolved and only executes the last enqueued
 * promise. Promises added between the last and the currently executing promise are skipped.
 * This is useful when earlier enqueued promises become obselete.
 * See: https://stackoverflow.com/questions/53540348/js-async-await-tasks-queue
 */
export class LastQueue {
    constructor() {
        this._nextPromise = null;
        this._pendingPromise = false;
    }

    enqueue(action, payload) {
        return new Promise((resolve, reject) => {
            this._nextPromise = { action, payload, resolve, reject };
            this.dequeue();
        });
    }

    async dequeue() {
        if (this._pendingPromise) {
            return false;
        }
        if (this._nextPromise) {
            let item = this._nextPromise;
            this._nextPromise = null;
            try {
                this._pendingPromise = true;
                let payload = await item.action(item.payload);
                this._pendingPromise = false;
                item.resolve(payload);
            } catch (e) {
                this._pendingPromise = false;
                item.reject(e);
            } finally {
                this.dequeue();
            }
            return true;
        }
        return false;
    }
}
