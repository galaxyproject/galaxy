/**
 * Same basic format as historyContentProvider, but it should be simpler than
 * the history because:
 *
 * 1. Collections are immutable after creation so they don't change over time,
 *    meaning there is no polling and no need to do "random access" as we do for
 *    histories since we can just limit/offset to reach everything since the
 *    total matches count will always be the same. A "total matches" exists in
 *    the basic content record in the form of "element_count", and we already
 *    have that value in the DSC which is passed in.
 *
 * 2. There is no filtering for collections on the server so all we can do is
 *    page through the results.
 */

import { NEVER, merge, combineLatest } from "rxjs";
import { map, pluck, switchMap, distinctUntilChanged, share, shareReplay, mapTo, debounceTime } from "rxjs/operators";
import { tag } from "rxjs-spy/operators/tag";
import { whenAny } from "utils/observable/whenAny";
import { activity } from "utils/observable/activity";
import { chunk } from "../../caching/operators/chunk";

import { DatasetCollection, SearchParams } from "../../model";
import { watchCollectionCache } from "./watchCollectionCache";
import { loadCollectionContents } from "./loadCollectionContents";
import { ContentProvider, scrollPosEquals, inputsSame } from "../ContentProvider";

export default {
    mixins: [ContentProvider],

    computed: {
        dsc() {
            if (this.parent instanceof DatasetCollection) {
                return this.parent;
            }
            return new DatasetCollection(this.parent);
        },
    },

    methods: {
        // prettier-ignore
        initStreams() {
            const {
                debouncePeriod,
                pageSize,
                params$,
                scrollPos$: rawScrollPos$
            } = this;

            //#region Raw Inputs

            const dsc$ = this.watch$("dsc", true).pipe(
                distinctUntilChanged(DatasetCollection.equals),
                tag("CollectionContentProvider-dsc"),
                shareReplay(1),
            );

            const distinctParams$ = params$.pipe(
                distinctUntilChanged(SearchParams.equals),
            );

            const inputs$ = whenAny(dsc$, distinctParams$).pipe(
                shareReplay(1),
            );

            const totalMatches$ = dsc$.pipe(
                pluck('totalElements'),
                tag("CollectionContentProvider-totalMatches"),
            );

            //#endregion

            //#region Scrolling

            const scrolling$ = rawScrollPos$.pipe(
                activity({ period: debouncePeriod }),
                shareReplay(1),
            );

            const scrollStart$ = inputs$.pipe(
                mapTo({ cursor: 0.0, key: null }),
            );

            const scrollPos$ = merge(scrollStart$, rawScrollPos$).pipe(
                distinctUntilChanged(scrollPosEquals),
                tag("CollectionContentProvider-scrollPos"),
                shareReplay(1),
            );

            //#endregion

            //#region Estimate element index from cursor + dsc

            const calculatedIndex$ = combineLatest([scrollPos$, totalMatches$]).pipe(
                debounceTime(0),
                map(([pos, totalMatches]) => this.getIndexFromPos(pos, totalMatches)),
                tag("CollectionContentProvider-calculatedIndex"),
            );

            const cursor$ = scrolling$.pipe(
                switchMap(isScrolling => isScrolling ? NEVER : calculatedIndex$),
                tag("CollectionContentProvider-cursor"),
            );

            //#endregion

            //#region Loading

            const loadCursor$ = cursor$.pipe(
                chunk(pageSize),
                tag('loadCursor'),
            );

            const loadInputs$ = whenAny(inputs$, loadCursor$).pipe(
                tag('loadInputs'),
                shareReplay(1),
            );

            const loadInputsThrottled$ = scrolling$.pipe(
                switchMap(isScrolling => isScrolling ? NEVER : loadInputs$),
                distinctUntilChanged(([inputsA, idxA], [inputsB, idxB]) => {
                    return idxA == idxB && inputsSame(inputsA, inputsB);
                }),
                map(([inputs, idx]) => [...inputs, idx]),
                tag('loadInputsThrottled'),
                share(),
            );

            const loader$ = loadInputsThrottled$.pipe(
                loadCollectionContents({ windowSize: 2 * pageSize }),
                tag('loader'),
                share(),
            );

            const loading$ = merge(loadInputsThrottled$, loader$).pipe(
                activity({ period: debouncePeriod }),
                tag('loading'),
                shareReplay(1),
            );

            //#endregion

            //#region Cache watcher

            const cacheCursor$ = cursor$.pipe(
                tag('cacheCursor'),
                shareReplay(1),
            );

            const cacheFromMonitor$ = inputs$.pipe(
                watchCollectionCache({
                    cursor$: cacheCursor$,
                    pageSize,
                    debouncePeriod
                }),
                tag("cacheFromMonitor"),
            );

            const cache$ = combineLatest([cacheFromMonitor$, totalMatches$]).pipe(
                debounceTime(0),
                map((inputs) => this.buildPayload(...inputs)),
                tag("cache"),
            );

            //#endregion

            return { scrollPos$, loader$, cache$, scrolling$, loading$ };
        },

        getIndexFromPos(pos, totalMatches) {
            const { cursor = null, key = null } = pos;
            if (key !== null) {
                return key;
            }
            if (cursor !== null) {
                return Math.round(Number(cursor) * totalMatches);
            }
            return 0;
        },

        buildPayload(result, totalMatches) {
            // console.log("buildPayload", result, totalMatches);
            const { contents } = result;
            const topRows = contents.length ? contents[0].element_index : 0;
            const bottomRows = Math.max(0, totalMatches - contents.length - topRows);
            return { ...result, topRows, bottomRows, totalMatches };
        },
    },
};
