/**
 * Observable operator that emits one value when the source
 * is emitting and another after it has stopped
 */

import { merge } from "rxjs";
import { mapTo, debounceTime, distinctUntilChanged, publish } from "rxjs/operators";

export const activity = (period = 500) => {
    return publish((src) => {
        const on = src.pipe(mapTo(true));
        const off = src.pipe(debounceTime(period), mapTo(false));
        return merge(on, off).pipe(distinctUntilChanged());
    });
};
