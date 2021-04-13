/**
 * Manual loading operators for content lists. These get run as the user scrolls
 * or filters data in the listing for immediate lookups. All of them will run
 * one or more ajax calls against the api and cache ther results.
 */
import { map, pluck, publish } from "rxjs/operators";
import { hydrate, nth, whenAny } from "utils/observable";
import { throttleDistinct } from "./operators/throttleDistinct";
import { requestWithUpdateTime } from "./operators/requestWithUpdateTime";

import { bulkCacheDscContent } from "./db";
import { SearchParams } from "../model/SearchParams";
import { ScrollPos } from "../model/ScrollPos";
import { prependPath } from "./workerConfig";
import { summarizeCacheOperation, dateStore } from "./loadHistoryContents";

/**
 * Load collection content (drill down)
 * Params: contents_url + search params + element_index
 */
// prettier-ignore
export const loadDscContent = (cfg = {}) => {

    return publish(src$ => {
        // clean and chunk inputs
        const inputs$ = src$.pipe(
            hydrate([undefined, SearchParams, ScrollPos]),
        );

        // add contents_url to cache data, will use it as a key
        const url$ = inputs$.pipe(nth(0));

        // request, throttle frequently repeated requests
        const ajaxResponse$ = inputs$.pipe(
            collectionContentAjaxLoad(cfg)
        );

        // Add in the url we found this content at because that is going to be like
        // a parent_id in the database
        const response$ = whenAny(ajaxResponse$, url$).pipe(
            map(([response, url]) => response.map((row) => ({ ...row, parent_url: url })))
        );

        const cached$ = response$.pipe(
            bulkCacheDscContent(), 
            summarizeCacheOperation(),
        );

        return cached$;
    });
};

// Separating this out so it's easier to mock for testing purposes
export const collectionContentAjaxLoad = (cfg = {}) => (inputs$) => {
    const { onceEvery = 10 * 1000 } = cfg;
    return inputs$.pipe(
        map(buildDscContentUrl),
        throttleDistinct({ timeout: onceEvery }),
        map(prependPath),
        requestWithUpdateTime({ dateStore }),
        pluck("response")
    );
};

// Collection + params -> request url w/o update_time
// ignore params for now, we don't filter collection contents yet.
const buildDscContentUrl = (inputs) => {
    // eslint-disable-next-line no-unused-vars
    const [url, filters, { offset = 0, limit = SearchParams.pageSize }] = inputs;
    const skipClause = offset ? `offset=${offset}` : "";
    const limitClause = limit ? `limit=${limit}` : "";
    const qs = [skipClause, limitClause].filter((o) => o.length).join("&");
    return `${url}?${qs}`;
};
