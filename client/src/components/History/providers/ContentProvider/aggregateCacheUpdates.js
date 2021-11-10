// Generalized bi-directional watch and aggregator.
// Looks at cache from starting index, then looks up and down

import { throwError, from, EMPTY } from "rxjs";
import {
    map,
    debounceTime,
    distinctUntilChanged,
    groupBy,
    reduce,
    mergeMap,
    switchMap,
    withLatestFrom,
    timeoutWith,
    ignoreElements,
} from "rxjs/operators";
import { show, debounceBurst, shareButDie } from "utils/observable";
import { SearchParams } from "../../model/SearchParams";
import { processContentUpdate, newUpdateMap, buildContentResult, getKeyForUpdateMap } from "./aggregation";
import { SEEK } from "../../caching/enums";
import { reportPayload } from "./helpers";

// prettier-ignore
export const aggregateCacheUpdates = (monitor, cfg = {}) => (src$) => {
    // monitor is a function that generates the update observable
    if (!(monitor instanceof Function)) {
        return throwError("monitor should be a function in aggregateCacheUpdates");
    }

    const {
        // number of rows we roughly expect to be in the window
        pageSize = SearchParams.pageSize,

        // input and output throttling
        debouncePeriod = 250,

        // field and key order for the contents
        keyField = "hid",
        keyDirection = SEEK.DESC,

        // reduces duplicate updates to the skiplist
        // which can be expensive
        updateGroupLifetime = 2 * debouncePeriod,

        debug = false,
    } = cfg;

    // function that extracts the key from a document
    const getKey = getKeyForUpdateMap(keyField);

    // incoming target key
    const targetKey$ = src$.pipe(shareButDie(1));

    // avoids creating a new monitor for every single key emission
    // chunk to ceiling if descending, floor if ascending
    const monitorInputKey$ = targetKey$.pipe(
        distinctUntilChanged(),
        show(debug, (key) => console.log("monitorInputKey", key)),
    );

    // incoming stream of cache updates
    // Monitor generation function is passed in via config so we can use it against different types of queries
    const cacheUpdates$ = monitorInputKey$.pipe(
        switchMap(monitor),
        show(debug, (change) => console.log("monitor output", change)),
    );

    // groups updates by skiplist key and debounces those
    // streams individually so we're not pointlessly updating
    // when we're just going to change it again shortly
    const groupedUpdates$ = cacheUpdates$.pipe(
        groupBy(
            update => update.key,
            update => update,
            updateByKey$ => updateByKey$.pipe(
                timeoutWith(updateGroupLifetime, EMPTY),
                ignoreElements()
            )
        ),
        // eliminates rapid double updates to same item
        mergeMap(updateByKey$ => updateByKey$.pipe(
            debounceTime(0.25 * debouncePeriod),
        )),
        debounceBurst(debouncePeriod),
        show(debug, changeBurst => console.log('burst', changeBurst.map(o => o.key))),
    );

    // aggregates changes into a skiplist.
    const storage = newUpdateMap();
    const currentMap$ = groupedUpdates$.pipe(
        mergeMap(updateList => from(updateList).pipe(
            reduce(processContentUpdate, storage)
        )),
        show(debug, () => console.log('grouped update burst done')),
    );

    const contentListInputs$ = currentMap$.pipe(
        withLatestFrom(targetKey$),
    );

    // query skiplist with scroll position (transformed into a key from the skiplist)
    // to produce list of nearby content
    const contentList$ = contentListInputs$.pipe(
        map(buildContentResult({ pageSize, keyDirection, getKey })),
        show(debug, payload => reportPayload(payload, { indexKey: keyField, label: "aggregateCacheUpdates payload" })),
    );

    return contentList$;
};
