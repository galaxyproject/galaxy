import { combineLatest, concat, race, timer, merge, partition, Observable, BehaviorSubject, Subject } from "rxjs";
import {
    debounceTime,
    distinctUntilChanged,
    filter,
    map,
    mapTo,
    mergeAll,
    pairwise,
    pluck,
    publish,
    share,
    shareReplay,
    take,
    tap,
    window,
    withLatestFrom,
} from "rxjs/operators";
import { chunk, show } from "utils/observable";
import { isValidNumber } from "utils/validation";
import { CurveFit } from "components/History/model/CurveFit";
import { ScrollPos } from "components/History/model/ScrollPos";
import { SearchParams } from "components/providers/History/SearchParams";
import { loadContents } from "./loadContents";
import { watchHistoryContents } from "./watchHistoryContents";
import { default as store } from "store/index";
import { defaultPayload } from "../ContentProvider";

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
        loadingTimeout = 2000,
        disablePoll = false,
        debug = false,
        // optional feedback indicators
        loadingEvents$ = new Subject(),
        resetPos$ = new Subject(),
        chunkSize = pageSize
    } = cfg;

    // These running totals are shared between instances of content payload because a lot of the
    // stats do not get returned on every single pol. That means the most recent values need to be
    // preserved when the user switches the filters back and forth
    const totalMatches$ = getSubject("totalMatches", history, filters, () => new BehaviorSubject(history.hidItems));
    const cursorToHid$ = getSubject("cursorToHid", history, filters, () => new BehaviorSubject(createCursorToHid(history)));
    const hidToTopRows$ = getSubject("hidToTopRows", history, filters, () => new BehaviorSubject(createHidToTopRows(history)));

    return publish((pos$) => {

        // #region establish HID by either having exact value or estimating from scroll position

        const [ noKey$, hasKey$ ] = partition(pos$, (pos) => pos.key === null);

        const knownHid$ = hasKey$.pipe(
            pluck('key')
        );

        const cursor$ = noKey$.pipe(
            pluck('cursor'),
        );

        // only have cursor height, need to make a guess
        const estimatedHid$ = combineLatest(cursor$, cursorToHid$).pipe(
            map((inputs) => estimateHid(...inputs)),
            map(hid => Math.round(hid)),
            distinctUntilChanged(),
            show(debug, hid => console.log("estimatedHid", hid, history)),
        );

        const hid$ = knownHid$.pipe(
            distinctUntilChanged(),
            filter(hid => !isNaN(hid)),
            share(),
        );

        // #endregion

        // #region server loading

        const serverHid$ = hid$.pipe(
            distinctUntilChanged(),
            debounceTime(debouncePeriod),
            show(debug, hid => console.log("serverHid", hid)),
            share(),
        );

        const serverLoad$ = serverHid$.pipe(
            tap(() => loadingEvents$.next(true)),
            loadContents({ history, filters, disablePoll, debug }),
            tap(() => loadingEvents$.next(false)),
            tap((response) => updateVuexHistory(history.id, response)),
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
            shareReplay(1)
        );

        const cachePayload$ = cacheMonitor$.pipe(
            withLatestFrom(totalMatches$, hidToTopRows$),
            map(buildPayload(pageSize)),
            show(debug, (payload) => console.log("payload", payload)),
        );

        // An empty cache response, wait a while then emit an empty payload
        const noResults$ = timer(loadingTimeout).pipe(
            mapTo({ ...defaultPayload, noResults: true }),
            take(1)
        );
        const noInitialResults$ = concat(noResults$, cachePayload$);
        const payload$ = race(noInitialResults$, cachePayload$);

        // #endregion

        // #region Reposition View to accomodate recent updates

        // When new updates to the history come in, we should shift the scrollPos so that we can see
        // them. Without some kind of explicit move, the system will think they're just random
        // updates that are happening outside the region of interest, and there would be no
        // particular reason to shift the view. But that's not ideal when you're already looking at
        // the top of the history and expect to see the most recent updates as they come in.

        const adjustedScrollPos$ = serverLoad$.pipe(
            pairwise(),
            filter(([a,b]) => !isNaN(a.maxHid) && !isNaN(b.maxHid)),
            withLatestFrom(pos$, hid$),
            map(([[lastResponse, response], pos, hid]) => {
                const updatesAtTop = response.maxHid >= lastResponse.maxHid;

                const scrollerExactlyAtTop = pos.cursor === 0 || pos.key === lastResponse.maxHid;
                const fudge = 2;
                const scrollNearLastTop = pos.key !== null ? Math.abs(pos.key - lastResponse.maxContentHid) < fudge : false;
                const scrollerAtTop = scrollerExactlyAtTop || scrollNearLastTop;

                if (updatesAtTop && scrollerAtTop) {
                    return ScrollPos.create({ cursor: 0, key: response.maxContentHid });
                }
                return null;
            }),
            filter(Boolean),
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
            sub.add(adjustedScrollPos$.subscribe(resetPos$));

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

// Need to stash these subjects in memory since we don't get the counts
// back on every single poll request

const subjects = new Map();

const getSubject = (label, history, filters, subjectFactory) => {
    const key = makeSubjectKey(label, history, filters);
    if (!subjects.has(key)) {
        subjects.set(key, subjectFactory());
    }
    return subjects.get(key);
};

const makeSubjectKey = (label, history, filters) => {
    return JSON.stringify({ label, historyId: history.id, filters: filters.export() });
};

/**
 * Updates the vuex history when a polling result comes back.
 * TODO: consider storing histories in cache instead of Vuex, since some users have very large lists
 * of histories.
 *
 * @param   {string}  historyId     History id from poll result
 * @param   {object}  pollResponse  Poll summary response
 */
const updateVuexHistory = (historyId, pollResponse) => {
    const getter = store.getters["betaHistory/getHistoryById"];
    const existingHistory = getter(historyId);
    const { historySize: size, historyEmpty: empty } = pollResponse;
    const history = { ...existingHistory, size, empty };
    store.dispatch("betaHistory/setHistory", history);
};
