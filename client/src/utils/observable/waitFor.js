import { NEVER, concat } from "rxjs";
import { takeUntil } from "rxjs/operators";

// emits source only after trigger emits once
export const waitFor = (trigger) => (src) => {
    const gap = NEVER.pipe(takeUntil(trigger));
    return concat(gap, src);
};
