import { merge } from "rxjs";
import { map, distinctUntilChanged, publish, withLatestFrom, share } from "rxjs/operators";
import { content$, dscContent$, buildContentId, buildCollectionId } from "./db/observables";
import { monitorQuery } from "./db/monitorQuery";
import { SearchParams } from "../model/SearchParams";
import { deepEqual } from "deep-equal";
import { hydrate } from "utils/observable";
import { SEEK } from "./enums";
import { matchesSelector } from "pouchdb-selector-core";

// history contents monitor
export const monitorHistoryContent = (cfg = {}) => {
    return twoWayMonitor({
        ...cfg,
        db$: content$,
        buildRequest: buildContentPouchRequest,
        aggregationKeyField: "hid",
    });
};

// collection contents monitor
export const monitorCollectionContent = (cfg = {}) => {
    return twoWayMonitor({
        ...cfg,
        db$: dscContent$,
        buildRequest: buildCollectionPouchRequest,
        aggregationKeyField: "element_index",
    });
};

/**
 * Search cache upward and downward from the scroll HID, filtering out results
 * which do not match params, we don't want to return the entire result set for
 * 2 reasons: it might be huge, and we might not yet have large sections of the
 * contents if the user is rapidly dragging the scrollbar to different regions
 */
// prettier-ignore
export const twoWayMonitor = (cfg = {}) => (src$) => {
    const {
        db$,
        aggregationKeyField,
        buildRequest = buildContentPouchRequest,
        pageSize = SearchParams.pageSize,
        inputDebounce = 100,
        debug = false,
    } = cfg;

    return src$.pipe(
        hydrate([undefined, SearchParams]), 
        publish(input$ => {

            const upRequest$ = input$.pipe(
                map(buildRequest({ seek: SEEK.ASC, pageSize })),
                distinctUntilChanged(deepEqual),
                share(),
            );
        
            const downRequest$ = input$.pipe(
                map(buildRequest({ seek: SEEK.DESC, pageSize })),
                distinctUntilChanged(deepEqual),
                share(),
            );
        
            // one page up
            const up$ = upRequest$.pipe(
                monitorQuery({ db$, inputDebounce, debug, label: "up" }),
                alsoMatchWith(downRequest$),
            );
        
            // current page + next page = 2 pages down
            const down$ = downRequest$.pipe(
                monitorQuery({ db$, inputDebounce, debug, label: "down" }),
                alsoMatchWith(upRequest$),
            );
        
            return merge(up$, down$)
        }),
        map((change) => {
            // don't bother sending back non-matching results
            // we're just going to delete them from the skiplist
            // using the aggregation key, so no need to serialize them
            const { match, doc, ...more} = change;
            const key = doc[aggregationKeyField];
            return match ? { key, match, doc, ...more } : { key, match, ...more };
        })
    );
};

// utility operator, checks to see if change matches with the other selector
const alsoMatchWith = (req$) => (change$) => {
    // As the scroller moves, a given row may no longer match in one query
    // but it may in the other, simply because it has moved from the "up" results
    // to the "down" results

    return change$.pipe(
        withLatestFrom(req$),
        map(([change, otherRequest]) => {
            const result = { ...change };
            result.match = change.match || matchesSelector(result.doc, otherRequest.selector);
            return result;
        })
    );
};

/**
 * Generate a PouchDB selector for a specified history, filters, and a rough
 * guess of where to start looking.
 *
 * Can't use skip because there might be big un-cached regions of the history
 * and we need to be able to select without loading everything
 */
export const buildContentPouchRequest = (cfg = {}) => (inputs) => {
    const { seek, pageSize = SearchParams.pageSize } = cfg;
    const [history_id, params, hid] = inputs;

    // look up or down from target hid
    const targetId = buildContentId({ history_id, hid });

    // SEEK.ASC means the top seek, HID > target
    const comparator = seek == SEEK.ASC ? "$gt" : "$lte";

    // one page above the target, then 2 after to get the current page and some buffer
    const pages = seek == SEEK.ASC ? 1 : 2;
    const limit = pages * pageSize;

    // index, will build if not existent
    const filterFields = Array.from(params.criteria.keys()).map((f) => params.getPouchFieldName(f));
    const fields = ["_id", "history_id", ...filterFields];
    const ddoc = "idx-" + fields.sort().join("-");

    const request = {
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

    return request;
};

// filters currently unused, but they could be if we add some filter UI
export const buildCollectionPouchRequest = (cfg = {}) => (inputs) => {
    const { seek, pageSize = SearchParams.pageSize } = cfg;

    // eslint-disable-next-line no-unused-vars
    const [parent_url, filters, element_index] = inputs;
    const targetId = buildCollectionId({ parent_url, element_index });

    // SEEK.ASC means above the target means element_index < target
    const comparator = seek == SEEK.ASC ? "$lt" : "$gte";

    // 3 pages total, 1 before, the current one, 1 after;
    const pages = seek == SEEK.ASC ? 1 : 2;
    const limit = pages * pageSize;

    // when searching upward we invert the sort because we want the
    // results closest to the target
    const idSort = seek == SEEK.ASC ? "desc" : "asc";

    const request = {
        selector: {
            _id: { [comparator]: targetId },
            parent_url: { $eq: parent_url },
        },
        sort: [{ _id: idSort }],
        limit,
        index: {
            fields: ["_id"],
            sort: [{ _id: "asc" }],
            name: "collection contents by parent_url and element_index ascending",
            ddoc: "idx-dsc-contents-by-url-and-element-asc",
        },
    };

    return request;
};
