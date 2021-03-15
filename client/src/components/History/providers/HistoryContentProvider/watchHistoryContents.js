import { of, combineLatest } from "rxjs";
import { map, switchMap, debounceTime, scan, share, distinctUntilChanged } from "rxjs/operators";
import { chunk } from "utils/observable";
import { monitorHistoryContent } from "../../caching";
import { SearchParams } from "../../model/SearchParams";
import { processContentUpdate, newUpdateMap, buildContentResult, getKeyForUpdateMap } from "../aggregation";

/**
 * Monitor history in the region of the cursor for the provided inputs
 *
 * @param {Observable} hid$ HID observable, HID of first row of scroller
 * @param {Object} cfg Config object, see below
 */
// prettier-ignore
export const watchHistoryContents = (cfg = {}) => src$ => {
    const {
        history,
        filters,

        // final page size for rendered content
        pageSize = SearchParams.pageSize,

        // input and output throttling
        debouncePeriod = 250,

        // field and key order for the contents
        keyField = "hid",
        keyDirection = "desc",

        // input hid chunk, reduces the number of monitors we create
        // width of the hid window to observe in the cache
        monitorChunk = 5 * pageSize,
        monitorPageSize = 5 * monitorChunk,
    } = cfg;

    const getKey = getKeyForUpdateMap(keyField);
    const aggregator = processContentUpdate({ getKey });
    const summarize = buildContentResult({ pageSize, keyDirection, getKey });
    
    const hid$ = src$.pipe(
        share(),
    );

    const chunkedHid$ = hid$.pipe(
        chunk(monitorChunk, true),
        distinctUntilChanged(),
        debounceTime(debouncePeriod),
    );

    const updates$ = chunkedHid$.pipe(
        switchMap(hid => of([history.id, filters, hid]).pipe(
            monitorHistoryContent({
                pageSize: monitorPageSize
            }),
        )),
    );

    const currentMap$ = updates$.pipe(
        scan(aggregator, newUpdateMap())
    );

    const result = combineLatest([currentMap$, hid$]).pipe(
        debounceTime(debouncePeriod),
        map(summarize)
    );

    return result;
};
