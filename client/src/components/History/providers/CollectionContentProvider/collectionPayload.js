import { of, Observable, Subject, partition, merge } from "rxjs";
import { tap, map, pluck, switchMap, publish, distinctUntilChanged, share, throttleTime } from "rxjs/operators";
import { chunk } from "utils/observable";
import { SearchParams } from "components/providers/History/SearchParams";
import { loadDscContent } from "components/providers/History/caching";
import { watchCollection } from "./watchCollection";

// prettier-ignore
export const collectionPayload = (cfg = {}) => {
    const {
        parent: dsc,
        filters = new SearchParams(),
        pageSize = SearchParams.pageSize,
        debug = false,
        loadingEvents$ = new Subject(),
        debouncePeriod = 100,
        chunkSize = pageSize
    } = cfg;

    const { totalElements: totalMatches, contents_url } = dsc;

    return publish((pos$) => {

        // split scroll position into objects where we exactly know which key to focus on, and those
        // where we have to figure out where to start
        const [ noKey$, hasKey$ ] = partition(pos$, (pos) => pos.key === null);

        // if we don't know the exact elementIndex we need to calculate it from the cursor (portion
        // of the total scroller height) and the total matches which we should have from the dsc props
        const calculatedIndex$ = noKey$.pipe(
            pluck('cursor'),
            map((cursor) => Math.round(cursor * totalMatches)),
        );
        const knownIndex$ = hasKey$.pipe(pluck('key'));
        const elementIndex$ = merge(knownIndex$, calculatedIndex$).pipe(share());

        // chunk the input to the server request so we don't request for every single mouse move
        const chunked$ = elementIndex$.pipe(
            chunk(chunkSize),
            distinctUntilChanged(),
        );

        // overlap one page before and one page after, 3 total pages queried
        const pagination$ = chunked$.pipe(
            map(targetRow => {
                const offset = Math.max(0, targetRow - pageSize);
                const limit = 3 * pageSize;
                return { offset, limit, targetRow };
            }),
        );

        const serverLoad$ = pagination$.pipe(
            throttleTime(debouncePeriod, undefined, { trailing: true }),
            switchMap(pagination => of([contents_url, filters, pagination]).pipe(
                tap(() => loadingEvents$.next(true)),
                loadDscContent({ debug }),
                tap(() => loadingEvents$.next(false)),
            )),
        );

        const payload$ = elementIndex$.pipe(
            watchCollection({ dsc, filters, ...cfg}),
            map((result) => {
                const { contents } = result;
                const topRows = contents.length ? contents[0].element_index : 0;
                const bottomRows = Math.max(0, totalMatches - contents.length - topRows);
                return { ...result, topRows, bottomRows, totalMatches };
            }),
        );

        return new Observable((obs) => {
            const watchSub = payload$.subscribe(obs);
            watchSub.add(serverLoad$.subscribe());
            return watchSub;
        });
    })
};
