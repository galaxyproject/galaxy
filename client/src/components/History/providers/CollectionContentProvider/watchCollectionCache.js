import { combineLatest } from "rxjs";
import { map, switchMap, scan, distinctUntilChanged, catchError } from "rxjs/operators";
import { tag } from "rxjs-spy/operators/tag";
import { chunk } from "utils/observable";
import { monitorDscQuery } from "../../caching";
import { processContentUpdate, newUpdateMap, buildContentResult, getKeyForUpdateMap } from "../aggregation";
import { SearchParams } from "../../model";

// prettier-ignore
export const watchCollectionCache = (cfg = {}) => input$ => {
    const {
        cursor$,
        pageSize = SearchParams.pageSize,
        monitorChunk = 5 * pageSize,
        monitorPageSize = 5 * monitorChunk,
        inputDebounce = 250,
        // outputDebounce = inputDebounce,
        keyField = "element_index",
        keyDirection = "asc",
    } = cfg;

    const getKey = getKeyForUpdateMap(keyField);
    const aggregator = processContentUpdate({ getKey });
    const summarize = buildContentResult({ pageSize, keyDirection, getKey });

    const contentMap$ = input$.pipe(
        switchMap(([{contents_url}, params]) => {

            const chunkedCursor$ = cursor$.pipe(
                chunk(monitorChunk, true),
                distinctUntilChanged(),
            );

            const monitorInput$ = chunkedCursor$.pipe(
                map((idx) => [contents_url, params, idx]),
                tag('monitorInputs'),
            );

            const request$ = monitorInput$.pipe(
                map(buildDscChildrenSelector(monitorPageSize)),
                tag('request'),
            );

            const monitorOutput$ = request$.pipe(
                monitorDscQuery({ inputDebounce }),
                tag('monitorOutput'),
            );

            // aggregate results in a map for each set of id + params
            const updateMap$ = monitorOutput$.pipe(
                scan(aggregator, newUpdateMap()),
            );

            return updateMap$;
        }),
    );

    const contentWindow$ = combineLatest([ contentMap$, cursor$ ]).pipe(
        // debounceTime(outputDebounce),
        map(summarize),
        tag('contentWindow'),
    );

    return contentWindow$.pipe(
        catchError(err => {
            console.warn("Error in watchHistoryContents", err);
            throw err;
        })
    );
};

// filters currently unused, but they could be if we add some filter UI
export const buildDscChildrenSelector = (pageSize) => (inputs) => {
    // console.log("buildDscChildrenSelector", pageSize, inputs);

    // eslint-disable-next-line no-unused-vars
    const [parent_url, filters, cursor] = inputs;
    const lowerLimit = Math.max(0, cursor - pageSize);

    const request = {
        selector: {
            _id: { $gte: `${parent_url}-${lowerLimit}` },
            parent_url: { $eq: parent_url },
        },
        sort: [{ _id: "asc" }],
        limit: pageSize,
        index: {
            fields: ["_id"],
            sort: [{ _id: "asc" }],
            name: "collection contents by parent_url and element_index ascending",
            ddoc: "idx-dsc-contents-by-url-and-element-asc",
        },
    };

    return request;
};
