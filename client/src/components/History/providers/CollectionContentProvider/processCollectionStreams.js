import { merge, combineLatest } from "rxjs";
import { map, pluck, distinctUntilChanged, share, debounceTime } from "rxjs/operators";
import { tag } from "rxjs-spy/operators/tag";
import { whenAny } from "utils/observable/whenAny";
import { activity } from "utils/observable/activity";
import { shareButDie } from "utils/observable/shareButDie";
import { chunk } from "../../caching/operators/chunk";

import { DatasetCollection, SearchParams } from "../../model";
import { watchCollectionCache } from "./watchCollectionCache";
import { loadCollectionContents } from "./loadCollectionContents";
import { loadInputsSame } from "../HistoryContentProvider/processHistoryStreams";

// prettier-ignore
export function processCollectionStreams(sources, settings) {
    const { debouncePeriod, pageSize } = settings;
    const { dsc$: rawDsc$, params$: rawParams$, scrollPos$ } = sources;

    //#region Clean up, filter, debounce raw inputs

    const dsc$ = rawDsc$.pipe(distinctUntilChanged(DatasetCollection.equals));
    const params$ = rawParams$.pipe(distinctUntilChanged(SearchParams.equals));
    const inputs$ = whenAny(dsc$, params$).pipe(tag('inputs'), share());
    const scrolling$ = scrollPos$.pipe(activity());
    const totalMatches$ = dsc$.pipe(pluck("totalElements"));

    //#endregion

    //#region Estimate element index from cursor + dsc

    const cursor$ = whenAny(scrollPos$, totalMatches$).pipe(
        map(([pos, totalMatches]) => getIndexFromPos(pos, totalMatches)),
        distinctUntilChanged(),
        tag('cursor'),
        shareButDie(1),
    );

    //#endregion

    //#region Loading

    const chunkedCursor$ = cursor$.pipe(
        chunk(pageSize), 
    );

    const loadInputs$ = whenAny(inputs$, chunkedCursor$).pipe(
        distinctUntilChanged(loadInputsSame),
        map(([inputs, idx]) => [...inputs, idx]),
        tag('loadInputs'),
        shareButDie(1)
    );

    const loadResult$ = loadInputs$.pipe(
        loadCollectionContents({ windowSize: 2 * pageSize }),
        tag('loadResult'),
    );

    const loading$ = merge(loadInputs$, loadResult$).pipe(
        activity(),
    );

    //#endregion

    //#region Cache watcher

    const cacheFromMonitor$ = inputs$.pipe(
        watchCollectionCache({
            cursor$,
            pageSize,
            debouncePeriod,
        }),
        tag('cacheFromMonitor'),
    );

    const payload$ = combineLatest(cacheFromMonitor$, totalMatches$).pipe(
        debounceTime(debouncePeriod),
        map((inputs) => buildPayload(...inputs)),
        tag('payload'),
    );

    //#endregion

    return { payload$, scrolling$, loading$ };
}

function getIndexFromPos(pos, totalMatches) {
    const { cursor = null, key = null } = pos;
    if (key !== null) {
        return key;
    }
    if (cursor !== null) {
        return Math.round(Number(cursor) * totalMatches);
    }
    return 0;
}

function buildPayload(result, totalMatches) {
    const { contents } = result;
    const topRows = contents.length ? contents[0].element_index : 0;
    const bottomRows = Math.max(0, totalMatches - contents.length - topRows);
    return { ...result, topRows, bottomRows, totalMatches };
}
