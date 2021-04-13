import { merge } from "rxjs";
import { map, distinctUntilChanged } from "rxjs/operators";
import { content$, dscContent$, buildContentId, buildCollectionId } from "./db/observables";
import { monitorQuery } from "./db/monitorQuery";
import { SearchParams } from "../model/SearchParams";
import { deepEqual } from "deep-equal";
import { hydrate, shareButDie, show } from "utils/observable";
import { SEEK } from "./enums";

// history contents monitor
export const monitorHistoryContent = (cfg = {}) => {
    const { aggregationKeyField = "hid", ...moreCfg } = cfg;
    return twoWayMonitor({
        ...moreCfg,
        db$: content$,
        buildRequest: buildContentPouchRequest,
        aggregationKeyField,
    });
};

// collection contents monitor
export const monitorCollectionContent = (cfg = {}) => {
    const { aggregationKeyField = "element_index", ...moreCfg } = cfg;
    return twoWayMonitor({
        ...moreCfg,
        db$: dscContent$,
        buildRequest: buildCollectionPouchRequest,
        aggregationKeyField,
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

    const input$ = src$.pipe(
        show(debug, ([id, filters, hid]) => console.log("twoWayMonitor inputs", id, hid)),
        hydrate([undefined, SearchParams]), 
        shareButDie(1)
    );

    // one page up
    const up$ = input$.pipe(
        map(buildRequest({ seek: SEEK.ASC, pageSize })),
        distinctUntilChanged(deepEqual),
        show(debug, (req) => console.log("twoWayMonitor request (up)", req.selector)),
        monitorQuery({ db$, inputDebounce, debug, label: "up" }),
        show(debug, ({ doc, match }) => console.log("twoWayMonitor response (up)", doc[aggregationKeyField], match)),
    );

    // current page + next page = 2 pages down
    const down$ = input$.pipe(
        map(buildRequest({ seek: SEEK.DESC, pageSize })),
        distinctUntilChanged(deepEqual),
        show(debug, (req) => console.log("twoWayMonitor request (down)", req.selector)),
        monitorQuery({ db$, inputDebounce, debug, label: "down" }),
        show(debug, ({ doc, match }) => console.log("twoWayMonitor response (down)", doc[aggregationKeyField], match)),
    );

    const change$ = merge(up$, down$).pipe(
        map((response) => {
            // don't bother sending back non-matching results
            // we're just going to delete them from the skiplist
            // using the aggregation key, so no need to serialize them
            const { match, doc, ...more} = response;
            const key = doc[aggregationKeyField];
            return match ? { key, match, doc, ...more } : { key, match, ...more };
        }),
        show(debug, update => {
            const { key, match } = update;
            console.log("monitorHistoryContent change", key, match);
        }),
    );

    return change$;
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
