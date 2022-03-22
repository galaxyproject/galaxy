import { pipe } from "rxjs";
import { groupBy, mergeMap, throttleTime } from "rxjs/operators";

/**
 * Emits distinct values as they show up, but repeated values are throttled
 * until the timout expires.
 *
 * @param {integer} timeout throttle duration
 */
export const throttleDistinct = (cfg = {}) => {
    const { timeout = 1000, selector = (value) => value } = cfg;

    // prettier-ignore
    return pipe(
        groupBy(selector),
        mergeMap((grouped) => grouped.pipe(
            throttleTime(timeout)
        ))
    );
};
