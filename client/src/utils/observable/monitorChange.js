import { interval, timer } from "rxjs";
import { map, filter, take, takeUntil } from "rxjs/operators";

// prettier-ignore
export function monitorChange(expression, cfg = {}) {
    const {
        spamTime = 100,
        timeout = 10000,
        isValid = (val) => val !== undefined
    } = cfg;

    const rawVal = interval(spamTime).pipe(
        map(() => expression()),
        filter(isValid),
        take(1),
        takeUntil(timer(timeout))
    );

    return rawVal;
}
