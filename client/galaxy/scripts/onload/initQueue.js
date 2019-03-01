/**
 * There's a bunch of little init scripts running around. They will become part
 * of the mounting logic for components one day, but for now I want them out of
 * the python templates.
 *
 * You can add more init functions using addInitialization either from a python
 * template, or from anywhere else in the code if you import the loadConfig
 * file.
 *
 * In a python template (the config object is attached to window in the browser):
 *    config.addInitialiation(function (galaxyInstance, config) { // your init } )
 * In any webpack script:
 *    import { addInitialization } from "onload";
 *    addInitialization((galaxyInstance, config) => { // do things });
 */

import { BehaviorSubject } from "rxjs";
import { filter } from "rxjs/operators";

const queue = new BehaviorSubject([]);

// don't emit unless there are things to initialize
export const initializations$ = queue.pipe(filter(list => list.length > 0));

export const addInitialization = (...fns) => {
    let nextInits = [...queue.getValue(), ...fns];
    queue.next(nextInits);
};

export const prependInitialization = (...fns) => {
    let nextInits = [...fns, ...queue.getValue()];
    queue.next(nextInits);
};

export const clearInitQueue = () => queue.next([]);
