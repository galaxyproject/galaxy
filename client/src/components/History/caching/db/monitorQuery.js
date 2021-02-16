import deepEqual from "deep-equal";
import { isObservable, partition, merge, concat, of, pipe } from "rxjs";
import { tap, map, switchMap, debounceTime, distinctUntilChanged, pluck, filter } from "rxjs/operators";
import { matchesSelector } from "pouchdb-selector-core";
import { find } from "./find";
import { changes } from "./changes";

/**
 * Turns a selector into a live cache result emitter.
 *
 * @param {Observable} db$ Observable PouchDB instance
 * @param {Observable} request$ Observable Pouchdb-find configuration
 */
// prettier-ignore
export const monitorQuery = (cfg = {}) => (request$) => {
    const { db$ = null, inputDebounce = 0 } = cfg;

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
            const idSet = new Set();

            // do a search of the cache first
            const initial$ = of(request).pipe(
                find(db$),
                tap((docs) => docs.forEach((doc) => idSet.add(doc._id))),
                map((docs) => ({ action: ACTIONS.INITIAL, initialMatches: docs })),
            );

            // later changes
            const changedDocs$ = db$.pipe(
                changes(),
                filter(update => update.doc !== undefined),
                pluck("doc"),
            );

            // split stream into insert/update/remove
            const docMatch = doc => matchesSelector(doc, selector);
            const [ inSet$, notInSet$ ] = partition(changedDocs$, doc => idSet.has(doc._id));
            const [ updateEvt$, removeEvt$ ] = partition(inSet$, docMatch);
            const insertEvt$ = notInSet$.pipe(filter(docMatch));

            // merge all updates
            const updates$ = merge(
                updateEvt$.pipe(
                    tap(doc => idSet.add(doc._id)),
                    map(doc => ({ action: ACTIONS.UPDATE, doc }))
                ),
                removeEvt$.pipe(
                    tap(doc => idSet.delete(doc._id)),
                    map(doc => ({ action: ACTIONS.REMOVE, doc }))
                ),
                insertEvt$.pipe(
                    tap(doc => idSet.add(doc._id)),
                    map(doc => ({ action: ACTIONS.ADD, doc }))
                ),
            );

            return concat(initial$, updates$);
        })
    );
};

// prettier-ignore
export const singleUpdateResult = () => {
    return pipe(
        map(update => {
            const { action, initialMatches = [], doc = null } = update;

            // if no match, result is undefined
            let result = null;

            switch (action) {
                case ACTIONS.INITIAL:
                    if (initialMatches.length) {
                        result = initialMatches[0];
                    }
                    break;
                case ACTIONS.REMOVE:
                    result = null;
                    break;
                case ACTIONS.UPDATE:
                case ACTIONS.ADD:
                    if (doc) {
                        result = doc;
                    }
                    break;
            }

            return result;
        })
    )
};

export const ACTIONS = {
    INITIAL: "INITIAL",
    ADD: "ADD",
    UPDATE: "UPDATE",
    REMOVE: "REMOVE",
    IGNORE: "IGNORE",
};
