import deepEqual from "deep-equal";
import { isObservable, concat, of } from "rxjs";
import { concatAll, map, switchMap, debounceTime, distinctUntilChanged, pluck, filter } from "rxjs/operators";
import { matchesSelector } from "pouchdb-selector-core";
import { find } from "./find";
import { changes } from "./changes";
import { show } from "utils/observable";

/**
 * Turns a selector into a live cache result emitter. Emits objects with
 * a document object and a match boolean flag ({ doc, match: true }) indicating
 * whether or not this document matches the request$ selector
 *
 * @param {Observable} db$ Observable PouchDB instance
 * @param {Observable} request$ Observable Pouchdb-find configuration
 */
// prettier-ignore
export const monitorQuery = (cfg = {}) => (request$) => {
    const { db$, inputDebounce = 0, debug = false, label } = cfg;

    if (!isObservable(db$)) {
        throw new Error("Please pass a pouch database observable to monitorQuery");
    }

    const debouncedRequest$ = request$.pipe(
        debounceTime(inputDebounce),
        distinctUntilChanged(deepEqual),
    );

    return debouncedRequest$.pipe(
        switchMap((request) => {
            const { selector } = request;
            const docMatch = doc => matchesSelector(doc, selector);

            // do a search of the cache first
            const initial$ = of(request).pipe(
                find(db$, { debug, label }),
                concatAll(),
                map((doc) => ({ doc, match: true, initial: true })),
                show(debug, (change) => console.log("monitorQuery: initial", change)),
            );

            // later changes
            const updates$ = db$.pipe(
                changes({ debug, label }),
                pluck("doc"),
                filter(Boolean),
                map((doc) => ({ doc, match: docMatch(doc), update: true })),
                show(debug, (change) => console.log("monitorQuery: update", change)),
            );

            return concat(initial$, updates$);
        }),
        show(debug, (change) => console.log("monitorQuery", change)),
    );
};
