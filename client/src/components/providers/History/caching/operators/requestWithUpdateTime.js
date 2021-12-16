import moment from "moment";
import { of, pipe } from "rxjs";
import { tap, map, mergeMap } from "rxjs/operators";
import { ajax } from "rxjs/ajax";
import { createDateStore } from "components/History/model/DateStore";

/**
 * Global url date-store, keeps track of the last time a specific url was
 * requested Can reset the update_time tracking by passing in a new datestore to
 * the operator configs
 */
export const requestDateStore = createDateStore("requestWithUpdateTime default");

/***
 * Check datestore to get the last time we did this request. Append
 * an update_time clause at the end of the GET url so we only take
 * the fresh updates. Mark the time after the request for future requests
 */
// prettier-ignore
export const requestWithUpdateTime = (config = {}) => {
    const {
        dateStore = requestDateStore,
        bufferSeconds = 0,
        dateFieldName = "update_time-gt",
        requestTime = moment.utc(),
        // indicates we don't want initial results
        noInitial = false,
        responseQualifier = (response) => response.status == 200
    } = config;

    // mark and flag this update-time, append to next request with same base
    return pipe(
        tap((url) => {
            if (noInitial && !dateStore.has(url)) {
                dateStore.set(url, moment.utc());
            }
        }),
        mergeMap((baseUrl) => of(baseUrl).pipe(
            appendUpdateTime({ dateStore, bufferSeconds, dateFieldName }),
            mergeMap(ajax),
            tap((response) => {
                if (responseQualifier(response)) {
                    dateStore.set(baseUrl, requestTime)
                }
            })
        ))
    );
};

/**
 * Takes a base URL appends an update_time-gt restriction based on the lst
 * time this URL was requestd as indicated by the dateStore.
 * (Async in case we choose to store the date in indexDb instead of localStorage)
 */
// prettier-ignore
const appendUpdateTime = (cfg = {}) => {
    const {
        dateStore = requestDateStore,
        dateFieldName = "update_time-gt",
    } = cfg;

    return pipe(
        map((baseUrl) => {
            if (!dateStore.has(baseUrl)) {return baseUrl;}
            const lastRequest = dateStore.get(baseUrl);
            const parts = [baseUrl, `${dateFieldName}=${lastRequest.toISOString()}`];
            const separator = baseUrl.includes("?") ? "&" : "?";
            return parts.join(separator);
        })
    );
};
