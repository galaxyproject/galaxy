/**
 * A conditional tap used for debugging so we don't have to constantly add and remove tap statements
 * while working on rxjs streams
 */
import { tap } from "rxjs/operators";

export const show = (flag = false, fn) => {
    return tap((val) => {
        if (flag) {
            fn(val);
        }
    });
};
