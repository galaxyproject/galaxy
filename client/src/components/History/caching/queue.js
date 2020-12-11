/**
 * Lossless backpressure queue for processing observables one at
 * a time without spamming the server or the cache.
 */
import { Subject } from "rxjs";
import { concatMap, publish, finalize, delay } from "rxjs/operators";

// put stuff on this Subject to process
// format { task: observable to run, label: some identifier }
const queue$ = new Subject();

// process each item sequentially
// prettier-ignore
const process$ = queue$.pipe(
    concatMap(({ task, label }) => {
        task.connect();
        return task.pipe(
            delay(100),
            finalize(() => console.log("[queue] task done", label))
        );
    })
);

// just a counter to help debugging
let taskCounter = 0;

// publish passed observable. This won't emit until later
// when connect() is called, throw the new task on the queue$;
export function enqueue(obs$) {
    const label = taskCounter++;
    const task = obs$.pipe(publish());
    queue$.next({ task, label });
    return task;
}

// subscribe to processor
export const queueSubscription = process$.subscribe(
    (result) => console.log("[queue] result", result),
    (err) => console.warn("[queue] error", err),
    () => console.warn("[queue] complete, why is queue complete?")
);
