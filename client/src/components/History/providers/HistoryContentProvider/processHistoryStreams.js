import { of, merge, BehaviorSubject } from "rxjs";
import {
    debounceTime,
    distinctUntilChanged,
    ignoreElements,
    map,
    pluck,
    share,
    switchMap,
    tap,
    withLatestFrom,
} from "rxjs/operators";
import { activity, chunk, shareButDie, whenAny } from "utils/observable";
import { propMatch, isLoading, isValidNumber } from "../helpers";
import { SearchParams, CurveFit } from "../../model";
import { loadContents } from "./loadContents";
import { watchHistoryContents } from "./watchHistoryContents";

/**
 * Takes incoming history, filters and scroll position and generates loading, scrolling and payload
 * observable for rendering the content. payload$ is an observable that emits the data that should
 * be displayed in the scroller
 *
 * @param   {object}  sources   object containing params$, history$, scrollPos$ source observables
 * @param   {object}  settings  configuration parameter object
 *
 * @return  {object}            payload$, loading$, scrolling$ observables
 */
// prettier-ignore
export function processHistoryStreams(sources = {}, settings = {}) {
    const { debouncePeriod = 0 } = settings;

    // clean incoming source streams
    const history$ = sources.history$.pipe(
        distinctUntilChanged(propMatch("id"))
    );
    const params$ = sources.params$.pipe(
        distinctUntilChanged(SearchParams.equals)
    );
    const pos$ = sources.scrollPos$.pipe(
        debounceTime(debouncePeriod),
        distinctUntilChanged(),
        share(),
    );

    // The actual loader, when history or params change we poll against the api and
    // set up a cachewatcher, both of which are controlled by the scroll position
    const loaderReset$ = whenAny(history$, params$);
    const payload$ = loaderReset$.pipe(
        switchMap(([history, filters]) => pos$.pipe(
            tap(val => console.log("exterior input", val)),
            contentPayload({ history, filters, ...settings })
        )),
        share()
    );

    // true while scroll position is changing
    const scrolling$ = sources.scrollPos$.pipe(activity());

    // true when params change, false when we emit first result
    // const loading$ = payload$.pipe(isLoading(loaderReset$));
    const loading$ = of(false);

    return { payload$, scrolling$, loading$ };
}

/**
 * Observable operator accepts history, search filters as config values, then uses an observable
 * scroll position to periodically poll the server for new data and watch the cache for
 * corresponding updates for a window of content defined by the cfg props.
 *
 * @param   {object}      cfg   history, filters, other operation parameters
 * @param   {Observable}  pos$  Observable scroll position
 *
 * @return  {Observable}        Observable that emits payloads suitable for use in the scroller
 */
// prettier-ignore
export const contentPayload = (cfg = {}) => (scrollPos$) => {
    const { 
        history, 
        filters = new SearchParams(),
        pageSize = SearchParams.pageSize, 
        debouncePeriod = 0 
    } = cfg;

    // locals
    const cursorToHid = createCursorToHid(history);
    const hidToTopRows = createHidToTopRows(history);

    // total search matches
    const knownMatches$ = new BehaviorSubject(0);
    const totalMatches$ = knownMatches$.pipe(distinctUntilChanged());

    // share
    const pos$ = scrollPos$.pipe(
        tap((pos) => console.log("input pos", pos)),
    );

    // turn pos.cursor into limit/offset for server polling pad it with a wide overlap so we get
    // some results outside the immediate area of interest
    const pagination$ = pos$.pipe(
        pluck("cursor"),
        chunk(pageSize / 4),
        withLatestFrom(totalMatches$),
        map(([ cursor, matches ]) => buildPaginationWindow(cursor, matches, pageSize)),
        debounceTime(debouncePeriod),
    );

    // Run a periodic poll, response will update totalMatches and the curve fits so the client can
    // figure out how to query using one of the data fields instead of an index, because that index
    // (the rownumber implicitly used by limit/offset) is useless to the client unless we store each
    // history contents separately
    const serverLoad$ = pagination$.pipe(
        loadContents({ history, filters }),
        tap((response) => {
            console.log("cursorToHid", cursorToHid);
            adjustCursorToHid(response, cursorToHid);
            console.log("cursorToHid.adjusted", cursorToHid);

            adjustHidToTopRows(response, hidToTopRows);
            knownMatches$.next(response.totalMatches);
        }),
        share()
    );

    // create a hid for the cache query, because we can't just query with a limit/offset against the
    // cache since the cache doesn't necessarily have enough content to calculate an offset
    const hid$ = pos$.pipe(
        map((pos) => {
            const hid = estimateHid(pos, cursorToHid);
            console.log("estimated hid", pos, hid);
            return hid;
        }),
    );
    const cacheMonitor$ = hid$.pipe(
        watchHistoryContents({ history, filters, pageSize, debouncePeriod })
    );
    const payload$ = whenAny(cacheMonitor$, totalMatches$).pipe(
        map(([cacheResult, totalMatches]) => buildPayload(cacheResult, totalMatches, hidToTopRows, pageSize))
    );

    // holds onto loader subscription for lifetime of the payload$ without emitting anything
    const loaderRunning$ = serverLoad$.pipe(ignoreElements());
    const result$ = merge(payload$, loaderRunning$);

    return result$;
};

/**
 * Creates limit/offset from scroll position and data set size, adds padding. This pagination is
 * used for the server-side content query where limit/offset will work
 *
 * @param   {float}  cursor    0-1 value representing how far down the history we are
 * @param   {int}    matches   total server-side known matches for content query result
 * @param   {int}    pageSize  scaling parameter, number of rows in a "page"
 * @param   {int}    pagePad   multiplier that pads the limit/offset for overlap
 *
 * @return  {object}           limit/offset for use in content query
 */
function buildPaginationWindow(cursor, matches, pageSize, pagePad = 2) {
    // this is where the cursor is pointed
    const target = cursor * matches;

    // get a bottom lip of the window in terms of limit/offset
    const offset = Math.max(0, target - pageSize);

    // double the window size so there's a window in the back
    // and one in the front so we're getting a good overlap
    const limit = pagePad * pageSize;

    return { offset, limit };
}

/**
 * Calculates a HID to use in caching queries from the scroll position
 *
 * @param   {object}    scrollPos    cursor (0-1), key (string) representing position in scroller
 * @param   {CurveFit}  cursorToHid  data points used to estimate hid value from cursor position
 *
 * @return  {int}                    HID
 */
function estimateHid(scrollPos, fit) {
    const { cursor, key } = scrollPos;

    // console.log("estimateHid", scrollPos, fit);

    // do an estimate/retrieval
    const result = fit.get(cursor, { interpolate: true });
    if (isValidNumber(result)) {
        // console.log("estimateHid (case 1)", result);
        return result;
    }

    // give them the top of the data
    if (fit.hasData) {
        // console.log("estimateHid (case 2)", scrollPos);
        console.log("invalid curve fit", result, cursor, key, fit.domain);
        return fit.get(0);
    }

    // we're screwed
    console.log("estimateHid no estimate available", scrollPos);
    return undefined;
}

function adjustCursorToHid(result, fit) {
    const { maxHid, minHid, maxContentHid, minContentHid, limit, offset, totalMatches } = result;

    // set 0, 1 for min/max hids
    fit.set(0.0, +maxHid);
    fit.set(1.0, +minHid);

    // find cursor for top & bottom of returned content
    // if (totalMatches > 0) {
    //     fit.set((1.0 * offset) / totalMatches, maxContentHid);
    //     fit.set((1.0 * (offset + limit)) / totalMatches, minContentHid);
    // }

    return fit;
}

function adjustHidToTopRows(result, fit) {
    const {
        // min and max of returned data
        minContentHid,
        maxContentHid,

        // endpoints for all of history, that match filters
        minHid,
        maxHid,

        // pagination params for this query
        offset,
        totalMatches,

        // count of rows returned, usually same as limit except when page is short
        matches,
    } = result;

    // endpoints for all content
    fit.set(maxHid, 0);
    fit.set(minHid, totalMatches - 1);

    // content range we returned
    fit.set(maxContentHid, offset);
    fit.set(minContentHid, offset + matches);

    // clamp
    fit.domain = [minHid, maxHid];

    return fit;
}

function buildPayload(cacheResult, totalMatches, hidToTopRows, pageSize) {
    const { contents = [], startKey = null } = cacheResult;

    let topRows = 0;
    let bottomRows = Math.max(0, totalMatches - contents.length);

    // missing rows above & below content
    if (hidToTopRows.size && contents.length && totalMatches > pageSize) {
        const maxHid = contents[0].hid;
        const rowsAboveTop = hidToTopRows.get(maxHid, { interpolate: true });
        topRows = Math.max(0, Math.round(rowsAboveTop));
        bottomRows = Math.max(0, totalMatches - topRows - contents.length);
    }

    return { contents, startKey, topRows, bottomRows, totalMatches };
}

/**
 * estimates offset (top rows) from hid for use in scroll rendering pads the top of the scroller
 * with a bunch of blank space representing the data we're not looking at right now
 *
 * @param   {Object}  history  current history
 * @return  {CurveFit}         object collecting data points for future estimation
 */
function createHidToTopRows(history) {
    const fit = new CurveFit();
    fit.domain = [0.0, +history.hidItems];
    fit.xPrecision = 3;
    fit.yPrecision = 3;
    fit.set(history.hidItems, 0.0);
    fit.set(0.0, history.hidItems);
    return fit;
}

function createCursorToHid(history) {
    const fit = new CurveFit();
    fit.domain = [0.0, 1.0];
    fit.xPrecision = 3;
    fit.yPrecision = 2;
    fit.set(0.0, history.hidItems);
    fit.set(1.0, 1);
    return fit;
}
