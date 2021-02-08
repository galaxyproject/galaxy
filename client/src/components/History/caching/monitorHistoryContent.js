import { merge, partition, concat } from "rxjs";
import { map, share, shareReplay, pluck, take, reduce, distinctUntilChanged } from "rxjs/operators";
import { content$, buildContentId } from "./db/observables";
import { monitorQuery, ACTIONS } from "./db/monitorQuery";
import { hydrate } from "./operators/hydrate";
import { SearchParams } from "../model/SearchParams";
import { deepEqual } from "deep-equal";

/**
 * Search cache upward and downward from the scroll HID, filtering out results
 * which do not match params, we don't want to return the entire result set for
 * 2 reasons: it might be huge, and we might not yet have large sections of the
 * contents if the user is rapidly dragging the scrollbar to different regions
 */
// prettier-ignore
export const monitorHistoryContent = (cfg = {}) => (src$) => {
    // console.warn("monitorHistoryContent operator", cfg);

    const {
        db$ = content$,
        pages = 1,
        pageSize = SearchParams.pageSize,
        bench = pages * pageSize,
        limit = pages * pageSize,
        inputDebounce = 0,
    } = cfg;

    const input$ = src$.pipe(
        hydrate([undefined, SearchParams]),
        shareReplay(1),
    );

    const up$ = input$.pipe(
        map(buildContentPouchRequest({
            seek: "asc",
            limit: bench
        })),
        distinctUntilChanged(deepEqual),
        monitorQuery({
            db$,
            inputDebounce,
        }),
    );

    const down$ = input$.pipe(
        map(buildContentPouchRequest({
            seek: "desc",
            limit
        })),
        distinctUntilChanged(deepEqual),
        monitorQuery({
            db$,
            inputDebounce,
        }),
    );


    // merge both up and down initial events into a single initial event
    // (reduces bouncing in the output)

    const all$ = merge(up$, down$).pipe(share());
    const splitter = evt => evt.action == ACTIONS.INITIAL;
    const [ allInital$, update$ ] = partition(all$, splitter);

    const initial$ = allInital$.pipe(
        pluck('initialMatches'),
        take(2),
        reduce((allDocs, docs) => allDocs.concat(docs), []),
        map(docs => ({ action: ACTIONS.INITIAL, initialMatches: docs })),
    );

    return concat(initial$, update$);
};

// seek types
export const SEEK = { ASC: "asc", DESC: "desc" };

/**
 * Generate a PouchDB selector for a specified history, filters, and a rough
 * guess of where to start looking.
 *
 * Can't use skip because there might be big un-cached regions of the history
 * and we need to be able to select without loading everything
 */
export const buildContentPouchRequest = (cfg = {}) => (inputs) => {
    const { limit = SearchParams.pageSize, seek = SEEK.DESC } = cfg;
    const [history_id, params, hid] = inputs;

    // look up or down from target hid
    const targetId = buildContentId({ history_id, hid });
    const comparator = seek == SEEK.ASC ? "$gt" : "$lte";

    // index, will build if not existent
    const filterFields = Array.from(params.criteria.keys()).map((f) => params.getPouchFieldName(f));
    const fields = ["_id", "history_id", ...filterFields];
    const ddoc = "idx-" + fields.sort().join("-");

    return {
        selector: {
            $and: [
                // doc id + direction (up/down)
                { _id: { [comparator]: targetId } },
                { history_id: history_id },
                ...params.pouchFilters,
            ],
        },
        sort: [{ _id: seek }],
        limit,
        index: {
            fields,
            ddoc,
        },
    };
};
