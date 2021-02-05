import { of, combineLatest } from "rxjs";
import { map, switchMap, debounceTime, scan, distinctUntilChanged } from "rxjs/operators";
import { chunk } from "../../caching/operators/chunk";
import { monitorHistoryContent } from "../../caching";
import { SearchParams } from "../../model/SearchParams";
import { processContentUpdate, newUpdateMap, buildContentResult, getKeyForUpdateMap } from "../aggregation";

// disable debugging
const tag = () => (src$) => src$;

/**
 * Monitor history in the region of the cursor for the provided inputs
 *
 * @param {Observable} hid$ HID observable, HID of first row of scroller
 * @param {Object} cfg Config object, see below
 */
// prettier-ignore
export const watchHistoryContents = (cfg = {}) => input$ => {
    const {
        hid$,

        // final page size for rendered content
        pageSize = SearchParams.pageSize,

        // input and output throttling
        debouncePeriod = 250,
        outputDebounce = debouncePeriod,

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

    const contentMap$ = input$.pipe(
        switchMap(([{id}, params]) => {

            // extremely wide chunking for the monitor since that's local
            // and assembling a new monitor is expensive. New monitors will be
            // created each time hid$ emits
            const monitorInput$ = hid$.pipe(
                chunk(monitorChunk, true),
                distinctUntilChanged(),
                map(hid => [id, params, hid]),
                tag('watchHistoryContents-monitorInputs'),
            );

            const monitorOutput$ = monitorInput$.pipe(
                switchMap(monitorInput => of(monitorInput).pipe(
                    monitorHistoryContent({
                        pageSize: monitorPageSize
                    }),
                )),
                scan(aggregator, newUpdateMap()),
            );

            return monitorOutput$;
        }),
    );

    // take a slice out of that content map corresponding to the current hid
    const contentWindow$ = combineLatest([contentMap$, hid$]).pipe(
        debounceTime(outputDebounce),
        map(summarize),
        tag('watchHistoryContents-contentWindow'),
    );

    return contentWindow$;
};
