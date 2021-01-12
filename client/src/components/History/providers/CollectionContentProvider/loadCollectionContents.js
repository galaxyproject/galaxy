import { of, pipe } from "rxjs";
import { switchMap, catchError } from "rxjs/operators";
import { tag } from "rxjs-spy/operators/tag";
import { loadDscContent } from "../../caching";

// prettier-ignore
export const loadCollectionContents = (cfg = {}) => {
    const {
        windowSize = 100
    } = cfg;

    return pipe(
        switchMap(([{contents_url}, params, idx]) => {
            const singleLoad$ = of([contents_url, params, idx]).pipe(
                tag('ajaxLoadInputs'),
                loadDscContent({ windowSize }),
            );
            return singleLoad$;
        }),
        catchError(err => {
            console.warn("Error in loadCollectionContents", err);
            throw err;
        })
    );
};
