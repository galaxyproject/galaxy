/**
 * Observable operator that emits one value when the source
 * is emitting and another after it has stopped
 */

import { merge } from "rxjs";
import { mapTo, delay, share } from "rxjs/operators";

export const activity = (cfg = {}) => (source) => {
    const { period = 500 } = cfg;
    const on = source.pipe(mapTo(true), share());
    const off = on.pipe(delay(period), mapTo(false));
    return merge(on, off);
};
