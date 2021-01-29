import { pipe } from "rxjs";
import { map, withLatestFrom, pluck, shareReplay } from "rxjs/operators";
import { throttleDistinct } from "utils/observable/throttleDistinct";
import { tag } from "rxjs-spy/operators/tag";

import { hydrate } from "./operators/hydrate";
import { requestWithUpdateTime, requestWithUpdateTimeNoInitial } from "./operators/requestWithUpdateTime";
import { prependPath } from "./workerConfig";
import { bulkCacheContent } from "./db";
import { SearchParams } from "../model/SearchParams";
import { createDateStore } from "../model/DateStore";

// Shared datestore for the request opertor for both loading and polling
export const dateStore = createDateStore();

export const clearHistoryDateStore = async () => {
    console.log("clearHistoryDateStore");
    dateStore.clear();
};

/**
 * Turn [historyId, params, hid] into content requests. Cache results and send
 * back statistics about what was returned for this query.
 */
// prettier-ignore
export const loadHistoryContents = (cfg = {}) => (rawInputs$) => {
    const {
        onceEvery = 30 * 1000,
        windowSize = SearchParams.pageSize,
        noInitial = false
    } = cfg;

    // if noInitial, only returns updates
    const dateAppender = noInitial ? requestWithUpdateTimeNoInitial : requestWithUpdateTime

    const inputs$ = rawInputs$.pipe(
        shareReplay(1)
    );

    const ajaxResponse$ = inputs$.pipe(
        hydrate([undefined, SearchParams]),
        map(([id, params, hid]) => {
            const baseUrl = `/api/histories/${id}/contents/near/${hid}/${windowSize}`;
            return `${baseUrl}?${params.historyContentQueryString}`;
        }),
        throttleDistinct({ timeout: onceEvery }),
        map(prependPath),
        dateAppender({ dateStore }),
        shareReplay(1),
    );

    const cacheSummary$ = ajaxResponse$.pipe(
        pluck("response"),
        bulkCacheContent(),
        summarizeCacheOperation(),
        tag("loadHistoryContents-cacheSummary"),
    );

    return cacheSummary$.pipe(
        withLatestFrom(ajaxResponse$, inputs$),
        map(([summary, ajaxResponse, inputs]) => {

            // actual list
            const { xhr, response = [] } = ajaxResponse;
            const { max: maxContentHid, min: minContentHid } = getPropRange(response, "hid");

            // header counts
            const matchesUp = +xhr.getResponseHeader("matches_up");
            const matchesDown = +xhr.getResponseHeader("matches_down");
            const totalMatchesUp = +xhr.getResponseHeader("total_matches_up");
            const totalMatchesDown = +xhr.getResponseHeader("total_matches_down");
            const minHid = +xhr.getResponseHeader("min_hid");
            const maxHid = +xhr.getResponseHeader("max_hid");

            return {
                // original inputs
                inputs,

                // cache summary
                summary,

                // derived from the returned content list
                minContentHid,
                maxContentHid,

                // ajax result stats
                minHid,
                maxHid,
                matchesUp,
                matchesDown,
                matches: matchesUp + matchesDown,
                totalMatchesUp,
                totalMatchesDown,
                totalMatches: totalMatchesUp + totalMatchesDown
            };
        })
    );
};

/**
 * Once data was cached, there's no need to send everything back over into the
 * main thread since the cache watcher will pick up those new values. This just
 * summarizes what pouchdb did during the bulk cache and sends back some stats.
 */
// prettier-ignore
export const summarizeCacheOperation = () => pipe(
    map((list) => {
        const cached = list.filter((result) => result.updated || result.ok);
        return {
            updatedItems: cached.length,
            totalReceived: list.length,
        };
    })
);

/**
 * Gets min and max values from an array of objects
 *
 * @param {Array} list Array of objects, each with a propName
 * @param {string} propName Name of prop to measure range
 */
export const getPropRange = (list, propName) => {
    const narrowRange = (range, row) => {
        const val = parseInt(row[propName], 10);
        range.max = Math.max(range.max, val);
        range.min = Math.min(range.min, val);
        return range;
    };

    const everywhere = {
        min: Infinity,
        max: -Infinity,
    };

    return list.reduce(narrowRange, everywhere);
};
