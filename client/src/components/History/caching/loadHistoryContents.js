import { zip } from "rxjs";
import { map, pluck, share } from "rxjs/operators";
import { hydrate } from "utils/observable";
import { requestWithUpdateTime } from "./operators/requestWithUpdateTime";
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
 * Turn [historyId, params, pagination] into content requests. Cache results and send
 * back statistics about what was returned for this query.
 */
// prettier-ignore
export const loadHistoryContents = (cfg = {}) => (rawInputs$) => {
    const { 
        noInitial = false,
        windowSize = SearchParams.pageSize
    } = cfg;

    const inputs$ = rawInputs$.pipe(
        hydrate([undefined, SearchParams]),
    );

    const ajaxResponse$ = inputs$.pipe(
        map(([id, params, hid]) => {
            const baseUrl = `/api/histories/${id}/contents/near/${hid}/${windowSize}`;
            return `${baseUrl}?${params.historyContentQueryString}`;
        }),
        map(prependPath),
        requestWithUpdateTime({ dateStore, noInitial }),
        share(),
    );

    const cacheSummary$ = ajaxResponse$.pipe(
        pluck("response"),
        bulkCacheContent(),
        summarizeCacheOperation(),
    );

    return zip(ajaxResponse$, cacheSummary$).pipe(
        map(([ajaxResponse, summary]) => {
            const { xhr, response = [] } = ajaxResponse;
            const { max: maxContentHid, min: minContentHid } = getPropRange(response, "hid");
            const headerInt = field => parseInt(xhr.getResponseHeader(field));

            // header counts
            const matchesUp = headerInt("matches_up");
            const matchesDown = headerInt("matches_down");
            const totalMatchesUp = headerInt("total_matches_up");
            const totalMatchesDown = headerInt("total_matches_down");
            const minHid = headerInt("min_hid");
            const maxHid = headerInt("max_hid");

            return {
                summary,
                matches: matchesUp + matchesDown,
                totalMatches: totalMatchesUp + totalMatchesDown,
                minHid,
                maxHid,
                minContentHid, // minimum hid in the returned result
                maxContentHid, // maximum hid in the returned result

                matchesUp,
                matchesDown,
                totalMatchesUp,
                totalMatchesDown,
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
export const summarizeCacheOperation = () => {
    return map((list) => {
        const cached = list.filter((result) => result.updated || result.ok);
        return {
            updatedItems: cached.length,
            totalReceived: list.length,
        };
    })
}

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
