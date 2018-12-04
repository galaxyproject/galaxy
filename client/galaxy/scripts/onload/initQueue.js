/**
 * There's a bunch of little init scripts running around. They will become part
 * of the mounting logic for components one day, but for now I want them out of
 * the python templates. Use this queue when it would be problematic to put
 * multiple webpack entry points onto the page with the lousy nested python
 * templates.
 */

import { BehaviorSubject } from "rxjs";
import { filter } from "rxjs/operators";

const queue = window.top._initQueue = new BehaviorSubject([]);

// don't emit unless there are things to initialize
export const initializations$ = queue.pipe(
    filter(list => list.length > 0)
);

export const addInitialization = (...fns) => {
    let nextInits = [ ...queue.getValue(), ...fns ];
    queue.next(nextInits);
}

export const prependInitialization = (...fns) => {
    let nextInits = [ ...fns, ...queue.getValue() ];
    queue.next(nextInits);
}

export const clearQueue = () => queue.next([]);
