import { zip } from "rxjs";
import { map, pluck, share, filter } from "rxjs/operators";
import { hydrate } from "utils/observable";
import { areDefined } from "utils/validation";
import { requestWithUpdateTime } from "./operators/requestWithUpdateTime";
import { prependPath } from "utils/redirect";
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

    const responseQualifier = ajaxResponse => ajaxResponse.status == 200 && ajaxResponse.response.length > 0;

    const ajaxResponse$ = inputs$.pipe(
        map(([id, params, hid]) => {
            const baseUrl = `/api/histories/${id}/contents/near/${hid}/${windowSize}`;
            return `${baseUrl}?${params.historyContentQueryString}`;
        }),
        map(prependPath),
        requestWithUpdateTime({ dateStore, noInitial, responseQualifier, dateFieldName: "since" }),
    );

    const validResponses$ = ajaxResponse$.pipe(
        filter(response => response.status == 200),
        share(),
    );

    const cacheSummary$ = validResponses$.pipe(
        pluck("response"),
        bulkCacheContent(),
        summarizeCacheOperation(),
    );

    return zip(validResponses$, cacheSummary$).pipe(
        map(([ajaxResponse, summary]) => {
            const { xhr, response = [] } = ajaxResponse;
            const { max: maxContentHid, min: minContentHid } = getPropRange(response, "hid");

            // return an int or undefined if the field does not exist in the headers
            const headerInt = field => {
                const raw = xhr.getResponseHeader(field);
                return raw === null ? undefined : parseInt(raw);
            };

            const headerBool = field => {
                const raw = xhr.getResponseHeader(field);
                return (raw == "true" || raw == "1");
            }

            // header counts
            const matchesUp = headerInt("matches_up");
            const matchesDown = headerInt("matches_down");
            const totalMatchesUp = headerInt("total_matches_up");
            const totalMatchesDown = headerInt("total_matches_down");
            const minHid = headerInt("min_hid");
            const maxHid = headerInt("max_hid");
            const historySize = headerInt("history_size");
            const historyEmpty = headerBool("history_empty");

            const matches = areDefined(matchesUp, matchesDown) ? matchesUp + matchesDown : undefined;
            const totalMatches = areDefined(totalMatchesUp, totalMatchesDown) ? totalMatchesUp + totalMatchesDown : undefined;

            return {
                summary,
                matches,
                totalMatches,
                minHid,
                maxHid,
                minContentHid, // minimum hid in the returned result
                maxContentHid, // maximum hid in the returned result

                matchesUp,
                matchesDown,
                totalMatchesUp,
                totalMatchesDown,

                // new history size
                historySize,
                historyEmpty
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
