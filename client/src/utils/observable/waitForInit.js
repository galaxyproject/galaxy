/**
 * Creates an observable that emits a single value once it appears, as defined by the selector
 * function. Emits that value and stops. Times out after designated period in the event that the
 * thing never shows up.
 */

import { interval, timer } from "rxjs";
import { map, filter, take, takeUntil } from "rxjs/operators";

// prettier-ignore
export function waitForInit(selector, cfg = {}) {
    const {
        spamTime = 100,
        timeout = 10000,
        isValid = (val) => val !== undefined
    } = cfg;

    return interval(spamTime).pipe(
        map(() => selector()),
        filter(isValid),
        take(1),
        takeUntil(timer(timeout))
    );
}

export function awaitValue(selector, cfg) {
    const val$ = waitForInit(selector, cfg);
    return val$.toPromise();
}
