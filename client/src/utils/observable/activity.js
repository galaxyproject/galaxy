/**
 * Observable operator that emits one value when the source
 * is emitting and another after it has stopped
 */

import { of, merge } from "rxjs";
import { throttleTime, mapTo, delay, switchMap, distinctUntilChanged } from "rxjs/operators";

// prettier-ignore
export const activity = (config = {}) => (source) => {
    const {
        // throttle period
        period = 500,
        // inactivity period
        trailPeriod = period,
        // active/inactive vals
        activeVal = true,
        inactiveVal = false,
    } = config;

    const active = source.pipe(
        mapTo(activeVal),
        throttleTime(period)
    );

    // each time one makes it past the goalie, start a timer for inactivity
    const inactive = active.pipe(
        switchMap(() => of(inactiveVal).pipe(
            delay(period + trailPeriod)
        ))
    );

    return merge(active, inactive).pipe(
        distinctUntilChanged()
    );
};
