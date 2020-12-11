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
// prettier-ignore
export const buildContentPouchRequest = (cfg = {}) => (inputs) => {
    const { limit = SearchParams.pageSize, seek = SEEK.DESC } = cfg;
    const [ history_id, params, hid ] = inputs;

    // look up or down from target
    const targetId = buildContentId({ history_id, hid });
    const comparator = (seek == SEEK.ASC) ? "$gt" : "$lte";

    const filters = buildContentSelectorFromParams(params);
    const fieldNames = new Set(['_id', 'history_id', ...Object.keys(filters)]);
    const idxName = "idx-" + Array.from(fieldNames).join("-");

    const request = {
        selector: {
            _id: { [comparator]: targetId },
            history_id: { $eq: history_id },
            ...filters,
        },
        sort: [{"_id": seek }],
        limit,
        index: {
            fields: Array.from(fieldNames),
            ddoc: idxName,
        }
    };

    return request;
};

/**
 * Build search selector for params filters:
 * deleted, visible, text search
 *
 * @param {SearchParams} params
 */
// prettier-ignore
export function buildContentSelectorFromParams(params) {
    const selector = {
        visible: { $eq: true },
        isDeleted: { $eq: false },
    };

    if (params.showDeleted) {
        delete selector.visible;
        selector.isDeleted = { $eq: true };
    }

    if (params.showHidden) {
        delete selector.isDeleted;
        selector.visible = { $eq: false };
    }

    if (params.showDeleted && params.showHidden) {
        selector.visible = { $eq: false };
        selector.isDeleted = { $eq: true };
    }

    const textFields = params.parseTextFilter();
    for (const [field, val] of textFields.entries()) {
        selector[field] = { $regex: new RegExp(val, "gi") };
    }

    return selector;
}
