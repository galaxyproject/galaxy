import { combineLatest, merge, Subject } from "rxjs";
import { tap, pluck, map, distinctUntilChanged, withLatestFrom, debounceTime, share } from "rxjs/operators";
import { tag } from "rxjs-spy/operators/tag";
import { whenAny } from "utils/observable/whenAny";
import { activity } from "utils/observable/activity";
import { shareButDie } from "utils/observable/shareButDie";
import { chunk } from "../../caching/operators/chunk";
import { nth } from "utils/observable/nth";

import { SearchParams, CurveFit } from "../../model";
import { watchHistoryContents } from "./watchHistoryContents";
import { loadContents } from "./loadContents";
import { isValidNumber, inputsSame } from "../ContentProvider";

// inputs + hid/cursor comparison
export const loadInputsSame = ([inputsA, cursorA], [inputsB, cursorB]) => {
    return cursorA == cursorB && inputsSame(inputsA, inputsB);
};

// prettier-ignore
export function processHistoryStreams(sources, settings) {
    const { disablePoll, debouncePeriod, pageSize } = settings;
    const { params$: rawParams$, history$: rawHistory$, scrollPos$ } = sources;

    //#region Clean up, filter, debounce raw inputs

    const history$ = rawHistory$.pipe(distinctUntilChanged((a, b) => a.id == b.id));
    const params$ = rawParams$.pipe(distinctUntilChanged(SearchParams.equals));
    const inputs$ = whenAny(history$, params$).pipe(share());
    const scrolling$ = scrollPos$.pipe(activity());

    //#endregion

    //#region Total Matches, from history and returned ajax stats

    const serverTotalMatches$ = new Subject();
    const historyMatches$ = history$.pipe(pluck("hidItems"));
    const totalMatches$ = merge(historyMatches$, serverTotalMatches$).pipe(distinctUntilChanged());

    //#endregion

    //#region Curve-fit objects, used to estimate hid & topRows

    const updateCursorToHid$ = new Subject();
    const updateHidToTopRows$ = new Subject();

    // reset curve-fit data whenever inputs change
    // same as history but emits each time inputs emits
    const h$ = inputs$.pipe(nth(0));
    const freshCursorToHid$ = h$.pipe(map(createCursorToHid));
    const freshHidToTopRows$ = h$.pipe(map(createHidToTopRows));

    // merge create + manual updates
    const cursorToHid$ = merge(freshCursorToHid$, updateCursorToHid$).pipe(shareButDie(1));
    const hidToTopRows$ = merge(freshHidToTopRows$, updateHidToTopRows$).pipe(shareButDie(1));

    //#endregion

    //#region Estimate HID from cursor + history + curveFit

    const hid$ = whenAny(scrollPos$, cursorToHid$).pipe(
        map(([pos, fit]) => (pos.key ? pos.key : estimateHid(pos, fit))),
        map((hid) => parseInt(hid)),
        distinctUntilChanged(),
        tag('hid'),
        shareButDie(1)
    );

    //#endregion

    //#region Loading

    const chunkedHid$ = hid$.pipe(chunk(pageSize, true));

    const loadInput$ = whenAny(inputs$, chunkedHid$).pipe(
        distinctUntilChanged(loadInputsSame),
        map(([inputs, hid]) => [...inputs, hid]),
        shareButDie(1)
    );

    const loadResult$ = loadInput$.pipe(
        loadContents({ disablePoll, windowSize: 2 * pageSize })
    );

    // side-effects of loading
    const loadEffects$ = loadResult$.pipe(
        withLatestFrom(cursorToHid$, hidToTopRows$),
        tap(([result, cursorToHid, hidToTopRows]) => {
            // can result in infinite loops, adjust curve-data by reference
            adjustCursorToHid(result, cursorToHid);
            adjustHidToTopRows(result, hidToTopRows);
            // updateHidToTopRows$.next();
            serverTotalMatches$.next(result.totalMatches);
        })
    );

    // loading flag
    const loading$ = merge(loadInput$, loadEffects$).pipe(activity());

    //#endregion

    //#region Use inputs to read from cache

    const cacheFromMonitor$ = inputs$.pipe(
        watchHistoryContents({
            hid$,
            pageSize,
            debouncePeriod,
        })
    );

    const payload$ = combineLatest(cacheFromMonitor$, hidToTopRows$, totalMatches$).pipe(
        debounceTime(debouncePeriod),
        map((inputs) => buildPayload(...inputs, pageSize))
    );

    //#endregion

    return { payload$, scrolling$, loading$ };
}

function estimateHid(scrollPos, cursorToHid) {
    const { cursor, key } = scrollPos;
    const fit = cursorToHid;

    // do an estimate/retrieval
    const result = fit.get(cursor, { interpolate: true });
    if (isValidNumber(result)) {
        return result;
    }

    // give them the top of the data
    if (fit.hasData) {
        console.log("invalid curve fit", result, cursor, key, fit.domain);
        return fit.get(0);
    }

    // we're screwed
    return undefined;
}

function adjustCursorToHid(result, fit) {
    const { maxHid, minHid, maxContentHid, minContentHid, matches, totalMatchesUp, totalMatches } = result;

    // set 0, 1 for min/max hids
    fit.set(0, maxHid);
    fit.set(1, minHid);

    // find cursor for top & bottom of returned content
    if (totalMatches > 0) {
        fit.set(totalMatchesUp / totalMatches, maxContentHid);
        fit.set((matches + totalMatchesUp) / totalMatches, minContentHid);
    }
}

function adjustHidToTopRows(result, fit) {
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
}

function buildPayload(result, hidToTopRows, totalMatches, pageSize) {
    const { contents = [], startKey = null, targetKey } = result;
    const fit = hidToTopRows;

    let topRows = 0;
    let bottomRows = Math.max(0, totalMatches - contents.length);
    // missing rows above & below content
    if (fit.size && contents.length && totalMatches > pageSize) {
        const maxHid = contents[0].hid;
        const rowsAboveTop = fit.get(maxHid, { interpolate: true });
        topRows = Math.max(0, Math.round(rowsAboveTop));
        bottomRows = Math.max(0, totalMatches - topRows - contents.length);
    }

    return { contents, startKey, targetKey, topRows, bottomRows, totalMatches };
}

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
