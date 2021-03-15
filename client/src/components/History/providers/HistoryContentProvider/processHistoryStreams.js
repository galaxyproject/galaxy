import { merge, partition, Observable, BehaviorSubject } from "rxjs";
import {
    debounceTime,
    distinctUntilChanged,
    map,
    share,
    switchMap,
    withLatestFrom,
    scan,
    pluck,
    publish,
} from "rxjs/operators";
import { activity, chunkProp, delayUntil, whenAny } from "utils/observable";
import { propMatch, isLoading, isValidNumber } from "../helpers";
import { SearchParams, CurveFit, ScrollPos } from "../../model";
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
    // clean incoming source streams
    const history$ = sources.history$.pipe(
        distinctUntilChanged(propMatch("id"))
    );
    const params$ = sources.params$.pipe(
        distinctUntilChanged(SearchParams.equals)
    );
    const pos$ = sources.scrollPos$.pipe(
        distinctUntilChanged(),
    );

    // The actual loader, when history or params change we poll against the api and
    // set up a cachewatcher, both of which are controlled by the scroll position
    const loaderReset$ = whenAny(history$, params$);
    const payload$ = loaderReset$.pipe(
        switchMap(([history, filters]) => pos$.pipe(
            contentPayload({ history, filters, ...settings })
        )),
        share()
    );

    // true while scroll position is changing
    const scrolling$ = sources.scrollPos$.pipe(activity());

    // true when params change, false when we emit first result
    const loading$ = payload$.pipe(isLoading(loaderReset$));

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
export const contentPayload = (cfg = {}) => src$ => {
    const { 
        history, 
        filters = new SearchParams(),
        pageSize = SearchParams.pageSize, 
        debouncePeriod = 200,
        disablePoll = false
    } = cfg;

    // total matches for history + filters as best known, gets updated
    // periodically as polls come back
    const totalMatches$ = new BehaviorSubject(0);

    return src$.pipe(
        debounceTime(debouncePeriod),
        distinctUntilChanged(ScrollPos.equals),
        publish(pos$ => {

            // Server loads
            const pagination$ = pos$.pipe(
                withLatestFrom(totalMatches$),
                map((inputs) => buildPaginationWindow(...inputs, pageSize)),
                chunkProp('offset', Math.floor(pageSize / 2)),
            );
            const serverLoad$ = pagination$.pipe(
                loadContents({ history, filters, disablePoll }),
                share(),
            );
            const cursorToHid$ = serverLoad$.pipe(
                scan(adjustCursorToHid, createCursorToHid(history)), 
            );
            const hidToTopRows$ = serverLoad$.pipe(
                scan(adjustHidToTopRows, createHidToTopRows(history)),
            );
            const serverMatches$ = serverLoad$.pipe(
                pluck('totalMatches')
            );

            // Determine cache watcher HID input by either reading it right off the scrollPos
            // or estimating it from the previously returned cursor/hid map, need to wait for
            // first content load response to start up the totalMatches and the estimation data

            const hidPos$ = pos$.pipe(delayUntil(serverLoad$));
            const [ needsEstimate$, hasKey$ ] = partition(hidPos$, pos => pos.key == null);

            const knownHid$ = hasKey$.pipe(pluck('key'));

            const estimatedHid$ = needsEstimate$.pipe(
                pluck('cursor'),
                withLatestFrom(cursorToHid$),
                map(([pos, cursorToHid]) => estimateHid(pos, cursorToHid)),
            );

            const hid$ = merge(knownHid$, estimatedHid$).pipe(
                map(key => Math.round(key)),
                distinctUntilChanged(),
            );

            // Cache Watching

            const cacheMonitor$ = hid$.pipe(
                watchHistoryContents({ history, filters, pageSize, debouncePeriod }),
            );

            const payload$ = cacheMonitor$.pipe(
                withLatestFrom(totalMatches$, hidToTopRows$),
                map(buildPayload(pageSize)),
            );

            // piggyback the subscriptions
            return new Observable((obs) => {
                const watchSub = payload$.subscribe(obs);
                // feed back the server-returned total matches into the process
                watchSub.add(serverMatches$.subscribe(totalMatches$));
                return watchSub;
            })
        })
    );
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
function buildPaginationWindow(pos, matches, pageSize, pagePad = 2) {
    const { cursor } = pos;

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
 * @param   {Number}    cursor    cursor (0-1) representing position in scroller
 * @param   {CurveFit}  cursorToHid  data points used to estimate hid value from cursor position
 *
 * @return  {int}                    HID
 */
function estimateHid(cursor, fit) {
    // do an estimate/retrieval
    const result = fit.get(cursor, { interpolate: true });
    if (isValidNumber(result)) {
        return result;
    }

    // give them the top of the data
    if (fit.hasData) {
        console.log("invalid curve fit", result, cursor, fit.domain);
        return fit.get(0);
    }

    // we're screwed
    console.log("estimateHid no estimate available");
    return undefined;
}

function adjustCursorToHid(fit, result) {
    const { maxHid, minHid, maxContentHid, minContentHid, offset, totalMatches, matches } = result;

    // set 0, 1 for min/max hids
    fit.set(0.0, +maxHid);
    fit.set(1.0, +minHid);

    // find cursor for top & bottom of returned content
    if (totalMatches > 0) {
        const topCursor = ((1.0 * offset) / totalMatches) * 1.0;
        const bottomCursor = ((1.0 * (offset + matches)) / totalMatches) * 1.0;
        fit.set(topCursor, maxContentHid);
        fit.set(bottomCursor, minContentHid);
    }

    return fit;
}

function adjustHidToTopRows(fit, result) {
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

const buildPayload = (pageSize) => (inputs) => {
    const [cacheResult, totalMatches, hidToTopRows] = inputs;
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
};

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
