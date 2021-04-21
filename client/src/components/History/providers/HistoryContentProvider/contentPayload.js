import { merge, partition, Observable, BehaviorSubject } from "rxjs";
import {
    tap,
    distinctUntilChanged,
    map,
    filter,
    share,
    withLatestFrom,
    pluck,
    publish,
    mergeAll,
    debounceTime,
    window,
} from "rxjs/operators";
import { chunk, show } from "utils/observable";
import { isValidNumber } from "../ContentProvider";
import { SearchParams, CurveFit } from "../../model";
import { loadContents } from "./loadContents";
import { watchHistoryContents } from "./watchHistoryContents";

/**
 * Observable operator accepts history, search filters as config values, then uses an observable
 * scroll position to periodically poll the server for new data and watch the cache for
 * corresponding updates for a window of content defined by the cfg props.
 *
 * @param   {object}      cfg   history, filters, other operation parameters
 * @return  {Observable}        Observable that emits payloads suitable for use in the scroller
 */
// prettier-ignore
export const contentPayload = (cfg = {}) => {
    const { 
        parent: history, 
        filters = new SearchParams(),
        pageSize = SearchParams.pageSize, 
        debouncePeriod = 250,
        disablePoll = false,
        debug = false,
        loading$ = new BehaviorSubject(),
    } = cfg;

    // stats for this history + filters, accumulates and improves over successive polls
    const totalMatches$ = new BehaviorSubject(0);
    const cursorToHid$ = new BehaviorSubject(createCursorToHid(history));
    const hidToTopRows$ = new BehaviorSubject(createHidToTopRows(history));

    return publish((pos$) => {

        // #region establish HID by either having exact value or estimating from scroll position

        const [ noKey$, hasKey$ ] = partition(pos$, (pos) => pos.key === null);

        const knownHid$ = hasKey$.pipe(
            pluck('key')
        );

        // only have cursor height, need to make a guess
        const estimatedHid$ = noKey$.pipe(
            pluck('cursor'),
            withLatestFrom(cursorToHid$),
            map((inputs) => estimateHid(...inputs)),
            map(hid => Math.round(hid)),
            show(debug, hid => console.log("estimatedHid", hid, history)),
        );

        const hid$ = merge(knownHid$, estimatedHid$).pipe(
            distinctUntilChanged(),
            filter(hid => !isNaN(hid)),
            share(),
        );
        
        // #endregion

        // #region server loading

        const serverHid$ = hid$.pipe(
            chunk(pageSize, true),
            distinctUntilChanged(),
            show(debug, hid => console.log("serverHid", hid)),
            share(),
        );

        const serverLoad$ = serverHid$.pipe(
            tap(() => loading$.next(true)),
            loadContents({ history, filters, disablePoll, debug }),
            share(),
        );

        //#endregion

        // #region Cache monitor

        // after a fresh server request has been made, wait for first response before allowing
        // an input to the cache, avoids bounciness
        const cacheHid$ = hid$.pipe(
            window(serverHid$),
            mergeAll(),
            debounceTime(100),
        );
        
        const cacheMonitor$ = cacheHid$.pipe(
            watchHistoryContents({ history, filters, pageSize, debouncePeriod, debug }),
            show(debug, (result) => console.log("cacheMonitor.contents (hid)", result.contents.map(o => o.hid))),
        );

        const payload$ = cacheMonitor$.pipe(
            withLatestFrom(totalMatches$, hidToTopRows$),
            map(buildPayload(pageSize)),
            tap(() => loading$.next(false)),
            show(debug, (payload) => console.log("payload", payload)),
        );

        // #endregion

        // #region serverLoad side-effects, keeps track of important stats via feedback loops

        const newCursorToHid$ = serverLoad$.pipe(
            withLatestFrom(cursorToHid$),
            map(([result, fit]) => adjustCursorToHid(result, fit))
        );

        const newHidToTopRows$ = serverLoad$.pipe(
            withLatestFrom(hidToTopRows$),
            map(([result, fit]) => adjustHidToTopRows(result, fit))
        );

        const newMatches$ = serverLoad$.pipe(
            pluck('totalMatches'),
            map(val => parseInt(val)),
        );

        //#endregion

        return new Observable((obs) => {
            const sub = payload$.subscribe(obs);

            // Tie stat feedback subscriptions to main payload sub
            // Make sure not to combineLatest these subject accumulators or we'll 
            // end up with an infinite loop
            sub.add(newCursorToHid$.subscribe(cursorToHid$));
            sub.add(newHidToTopRows$.subscribe(hidToTopRows$));
            sub.add(newMatches$.subscribe(totalMatches$));

            return sub;
        })
    })
};

const estimateHid = (cursor, fit) => {
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
};

const adjustCursorToHid = (result, fit) => {
    const { maxHid, minHid, maxContentHid, minContentHid, matches, totalMatchesUp, totalMatches } = result;

    // set 0, 1 for min/max hids
    fit.set(0, maxHid);
    fit.set(1, minHid);

    // find cursor for top & bottom of returned content
    if (totalMatches > 0) {
        fit.set(totalMatchesUp / totalMatches, maxContentHid);
        fit.set((matches + totalMatchesUp) / totalMatches, minContentHid);
    }

    return fit;
};

const adjustHidToTopRows = (result, fit) => {
    const {
        // min and max of returned data
        minContentHid,
        maxContentHid,

        // endpoints for all of history, that match filters
        minHid,
        maxHid,

        // num matches up/down from request hid
        matchesUp,
        matchesDown,
        matches,

        // total matches up/down from request hid
        totalMatchesUp,
        totalMatches,
    } = result;

    if (matches > 0) {
        fit.set(maxContentHid, totalMatchesUp - matchesUp);
        fit.set(minContentHid, Math.max(0, totalMatchesUp + matchesDown - 1));
    }

    fit.set(maxHid, 0);
    if (totalMatches > 0) {
        fit.set(minHid, totalMatches - 1);
    }

    fit.domain = [minHid, maxHid];

    return fit;
};

const buildPayload = (pageSize) => (inputs) => {
    // cacheWatchResult is the value from the cache watcher
    // hidToTopRows is a dataset for estimating toprows from HID
    // since we can't possibly have that information at the time
    // of the cache-read
    const [cacheWatchResult, totalMatches, hidToTopRows] = inputs;

    // contents is the list from the aggregator
    // targetKey was the request value for the aggregation
    const { contents = [] } = cacheWatchResult;

    let topRows = 0;
    let bottomRows = Math.max(0, totalMatches - contents.length - 1);

    // missing rows above & below content
    if (hidToTopRows.size && contents.length && totalMatches > pageSize) {
        const maxHid = contents[0].hid;
        const rowsAboveTop = hidToTopRows.get(maxHid, { interpolate: true });
        topRows = Math.max(0, Math.round(rowsAboveTop));
        bottomRows = Math.max(0, totalMatches - topRows - contents.length);
    }

    return { topRows, bottomRows, totalMatches, ...cacheWatchResult };
};

const createHidToTopRows = (history) => {
    const fit = new CurveFit();
    fit.domain = [0.0, +history.hidItems];
    fit.xPrecision = 3;
    fit.yPrecision = 3;
    fit.set(history.hidItems, 0.0);
    fit.set(0.0, history.hidItems);
    return fit;
};

const createCursorToHid = (history) => {
    const fit = new CurveFit();
    fit.domain = [0.0, 1.0];
    fit.xPrecision = 3;
    fit.yPrecision = 2;
    fit.set(0.0, history.hidItems);
    fit.set(1.0, 1);
    return fit;
};
