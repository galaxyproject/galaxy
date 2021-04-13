import { of, Observable, BehaviorSubject } from "rxjs";
import { tap, map, pluck, switchMap, share, debounceTime } from "rxjs/operators";
import { chunkProp, show } from "utils/observable";
import { SearchParams } from "../../model/SearchParams";
import { buildPaginationWindow } from "../ContentProvider";
import { loadDscContent } from "../../caching";
import { watchCollection } from "./watchCollection";
// import { reportPayload } from "../../test/providerTestHelpers";

// prettier-ignore
export const collectionPayload = (cfg = {}) => pos$ => {
    const {
        parent: dsc,
        filters = new SearchParams(),
        totalMatches = dsc.totalElements,
        pageSize = SearchParams.pageSize,
        debouncePeriod = 250,
        debug = false,
        loading$ = new BehaviorSubject(),
    } = cfg;

    const { contents_url } = dsc;

    const cursor$ = pos$.pipe(
        pluck('cursor'),
        show(debug, cursor => console.log("collectionPayload input cursor", cursor)),
        share()
    );

    // Server loads

    const pagination$ =  cursor$.pipe(
        map((cursor) => buildPaginationWindow(cursor, totalMatches, pageSize)),
        chunkProp('offset', pageSize / 2),
        show(debug, pagination => console.log("collectionPayload pagination", pagination)),
    );

    const serverLoad$ = pagination$.pipe(
        tap(() => loading$.next(true)),
        switchMap(pagination => of([contents_url, filters, pagination]).pipe(
            loadDscContent(),
        )),
        show(debug, val => console.log("collectionPayload loadDscContent response", val)),
    );

    // Cache Watcher
    // convert cursor to key: element_index, this is a lot easier than on
    // history because we don't filter (yet) and the index is numeric starting
    // at the top, so all we have to do is scale it
    const payload$ = cursor$.pipe(
        map((cursor) => cursor * totalMatches),
        watchCollection({ dsc, filters, ...cfg}),
        debounceTime(debouncePeriod),
        map((result) => {
            const { contents } = result;
            const topRows = contents.length ? contents[0].element_index : 0;
            const bottomRows = Math.max(0, totalMatches - contents.length - topRows);
            return { ...result, topRows, bottomRows, totalMatches };
        }),
    );

    // create observable that looks at the cache but piggybacks the loader subscription
    // piggyback the subscriptions
    return new Observable((obs) => {
        const watchSub = payload$.subscribe(obs);
        watchSub.add(serverLoad$.subscribe());
        return watchSub;
    })
};
