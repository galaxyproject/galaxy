export class ActionSkippedError extends Error {
    constructor(message = "Action skipped") {
        super(message);
        this.name = "ActionSkippedError";
    }
}

interface QueuedAction<T extends (arg: any, signal?: AbortSignal) => Promise<R>, R> {
    action: T;
    arg: Parameters<T>[0];
    resolve: (value: R | undefined) => void;
    reject: (error: Error) => void;
    controller: AbortController;
}

/**
 * A per-key async queue ensuring that only the latest enqueued task runs.
 * The first task starts immediately; later tasks replace pending ones.
 * Once the current task completes, any most recent queued task executes next.
 */
export class LastQueue<T extends (arg: any, signal?: AbortSignal) => Promise<R>, R = any> {
    private throttle: number;
    private rejectSkipped: boolean;
    private queues = new Map<string | number, QueuedAction<T, R>>();
    private pending = new Map<string | number, boolean>();
    private lastRun = new Map<string | number, number>();
    private timeoutIds = new Map<string | number, NodeJS.Timeout>();

    constructor(throttle = 1000, rejectSkipped = false) {
        this.throttle = throttle;
        this.rejectSkipped = rejectSkipped;
    }

    private skip(item: QueuedAction<T, R>) {
        item.controller.abort();
        if (this.rejectSkipped) {
            item.reject(new ActionSkippedError());
        } else {
            item.resolve(undefined);
        }
    }

    async enqueue(action: T, arg: Parameters<T>[0], key: string | number = "default"): Promise<R | undefined> {
        const controller = new AbortController();
        const task: QueuedAction<T, R> = { action, arg, resolve: () => {}, reject: () => {}, controller };
        return new Promise((resolve, reject) => {
            task.resolve = resolve;
            task.reject = reject;
            if (this.queues.has(key)) {
                const prev = this.queues.get(key)!;
                this.queues.delete(key);
                this.skip(prev);
            }
            this.queues.set(key, task);
            if (!this.pending.has(key)) {
                this.execute(key);
            }
        });
    }

    private async execute(key: string | number) {
        if (this.queues.has(key) && !this.pending.has(key)) {
            const task = this.queues.get(key)!;
            this.queues.delete(key);
            this.pending.set(key, true);
            this.lastRun.set(key, Date.now());
            try {
                if (task.controller.signal.aborted) {
                    throw new Error("Aborted");
                }
                const result = await task.action(task.arg, task.controller.signal);
                if (task.controller.signal.aborted) {
                    throw new Error("Aborted");
                }
                task.resolve(result);
            } catch (e: any) {
                if (e.message === "Aborted") {
                    if (this.rejectSkipped) {
                        task.reject(new ActionSkippedError());
                    } else {
                        task.resolve(undefined);
                    }
                } else {
                    task.reject(e);
                }
            } finally {
                this.pending.delete(key);
                this.next(key);
            }
        }
    }

    private next(key: string | number) {
        if (this.queues.has(key)) {
            const last = this.lastRun.get(key) || 0;
            const remaining = Math.max(0, this.throttle - (Date.now() - last));
            if (remaining === 0) {
                this.execute(key);
            } else {
                const id = setTimeout(() => {
                    this.timeoutIds.delete(key);
                    this.execute(key);
                }, remaining);
                this.timeoutIds.set(key, id);
            }
        }
    }
}
