/**
 * Manual loading operators for content lists. These get run as the user scrolls
 * or filters data in the listing for immediate lookups. All of them will run
 * one or more ajax calls against the api and cache ther results.
 */
import { map, pluck, withLatestFrom, publish } from "rxjs/operators";
import { nth } from "utils/observable";
import { requestWithUpdateTime } from "./operators/requestWithUpdateTime";
import { bulkCacheDscContent } from "./db";
import { SearchParams } from "../model/SearchParams";
import { prependPath } from "utils/redirect";
import { summarizeCacheOperation, dateStore } from "./loadHistoryContents";
import { show } from "utils/observable";

/**
 * Load collection content (drill down)
 * Params: contents_url + search params + element_index
 */
export const loadDscContent = (cfg = {}) => {
    const { debug = false } = cfg;

    return publish((inputs$) => {
        const url$ = inputs$.pipe(nth(0));

        return inputs$.pipe(
            map(buildDscContentUrl),
            map(prependPath),
            show(debug, (url) => console.log("Sending collection request:", url)),
            requestWithUpdateTime({ dateStore }),
            pluck("response"),
            withLatestFrom(url$),
            map(([rows, parent_url]) => {
                return rows.map((row) => ({ ...row, parent_url }));
            }),
            bulkCacheDscContent(),
            summarizeCacheOperation()
        );
    });
};

// Collection + params -> request url w/o update_time
// ignore params for now, we don't filter collection contents yet.
const buildDscContentUrl = (inputs) => {
    const [base, , pagination] = inputs;
    const { offset = 0, limit = SearchParams.pageSize } = pagination;
    const skipClause = offset ? `offset=${offset}` : "";
    const limitClause = limit ? `limit=${limit}` : "";
    const qs = [skipClause, limitClause].filter((o) => o.length).join("&");
    return `${base}?${qs}`;
};
