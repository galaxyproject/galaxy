/**
 * Manual loading operators for content lists. These get run as the user scrolls
 * or filters data in the listing for immediate lookups. All of them will run
 * one or more ajax calls against the api and cache ther results.
 */
import { map, withLatestFrom, pluck } from "rxjs/operators";
import { throttleDistinct, chunkParam } from "utils/observable";
import { nth } from "utils/observable/nth";

import { bulkCacheDscContent } from "./db";
import { prependPath } from "./workerConfig";
import { hydrate } from "./operators/hydrate";
import { requestWithUpdateTime } from "./operators/requestWithUpdateTime";
import { summarizeCacheOperation, dateStore } from "./loadHistoryContents";
import { SearchParams } from "../model/SearchParams";

/**
 * Load collection content (drill down)
 * Params: contents_url + search params + element_index
 */
// prettier-ignore
export const loadDscContent = (cfg = {}) => (src$) => {

    const {
        onceEvery = 10 * 1000,
        chunkSize = SearchParams.pageSize
    } = cfg;

    // clean and chunk inputs
    const inputs$ = src$.pipe(
        hydrate([undefined, SearchParams]),
        chunkParam(2, chunkSize)
    );

    // add contents_url to cache data, will use it as a key
    const url$ = inputs$.pipe(nth(0));

    // request, throttle frequently repeated requests
    const ajaxResponse$ = inputs$.pipe(
        map(buildDscContentUrl),
        throttleDistinct({ timeout: onceEvery }),
        map(prependPath),
        requestWithUpdateTime({ dateStore }),
        pluck("response")
    );

    // Add in the url we found this content at because that is going to be like
    // a parent_id in the database
    const response$ = ajaxResponse$.pipe(
        withLatestFrom(url$),
        map(([response, url]) => response.map((row) => ({ ...row, parent_url: url })))
    );

    const cached$ = response$.pipe(
        bulkCacheDscContent(),
        summarizeCacheOperation()
    );

    return cached$; // enqueue(load$, "load contents");
};

// Collection + params -> request url w/o update_time
// ignore params for now, we don't filter collection contents yet.
export const buildDscContentUrl = (inputs) => {
    // eslint-disable-next-line no-unused-vars
    const [url, filters, cursor] = inputs;
    const limit = SearchParams.pageSize;
    const skipClause = cursor ? `offset=${cursor}` : "";
    const limitClause = limit ? `limit=${limit}` : "";
    const qs = [skipClause, limitClause].filter((o) => o.length).join("&");
    return `${url}?${qs}`;
};
