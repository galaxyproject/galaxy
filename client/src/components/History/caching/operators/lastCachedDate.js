import moment from "moment";
import { pipe } from "rxjs";
import { map } from "rxjs/operators";
import { find } from "../db/find";

/**
 * Returns latest cache date from the cache.
 *
 * This seemingly simple calculation is complicated because the galaxy API
 * currently returns update_times that are more precise than javascript dates.
 *
 * For example. The server will return an update_time as:
 *     2020-07-02T17:25:09.385026
 *
 * When parsing a javascript date, however, we don't have that many decimals.
 *     2020-07-02T17:25:09Z
 *
 * This means that trying to perform an inequality filter:
 *     update_time-gt=2020-07-02T17:25:09Z
 *
 * ...will always fail because of those extra fractions of a millisecond. And
 * given the granularity of the date storage it is not safe to "just add one
 * more" to the outgoing value, given that there may indeed be lost records if we do that.
 *
 * source stream: pouchdb-find query config
 */
// prettier-ignore
export const lastCachedDate = (db$) => pipe(
    find(db$),
    map((docs) => {
        if (!docs.length) {return null;}
        const dates = docs.map((d) => d.cached_at);
        const maxDate = Math.max(...dates);
        return moment.utc(maxDate).toISOString();
    })
)
