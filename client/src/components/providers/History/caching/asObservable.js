/**
 * Worker client utility
 *
 * asObservable takes an observable transformation and persists its state while
 * it is running inside the worker. Normally when threads.js invokes an
 * observable, it runs once, its subscription ends and subsequent calls to that
 * same exposed function will start a new subscription.
 *
 * With asObservable, a subject is created inside the worker and subsequent
 * method calls put their new value on that Subject, which is connected to the
 * wrapped observable. Therefore the observable state is preserved until it is
 * explicitly unsubscribed from the outside, and distinct(), scan(), or other
 * stateful observable operators will continue to work.
 */
import { Subject, of } from "rxjs";
import { startWith } from "rxjs/operators";

// prettier-ignore
export const asObservable = (operator) => {
    const currentSubs = new Map();

    // process notifications
    // materialize exposed a "kind" variable for all observable messages,
    // it's either N,C,E for next, complete, error
    return ({ id, cfg = {}, value, kind }) => {

        if (kind == "N") {
            if (!currentSubs.has(id)) {
                const input$ = new Subject();
                const output$ = input$.pipe(startWith(value), operator(cfg));
                currentSubs.set(id, { input$, output$ });
                return output$;
            }
            const sub = currentSubs.get(id);
            sub.input$.next(value);
        }

        if (kind == "C" || kind == "E") {
            const sub = currentSubs.get(id);
            if (sub) {
                sub.input$.complete();
                currentSubs.delete(id);
            }
        }

        return of(null);
    };
};
