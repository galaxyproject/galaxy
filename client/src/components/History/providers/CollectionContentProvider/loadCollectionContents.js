import { of } from "rxjs";
import { switchMap } from "rxjs/operators";
import { tag } from "rxjs-spy/operators/tag";
import { loadDscContent } from "../../caching";

export const loadCollectionContents = (cfg = {}) => {
    const { windowSize = 100 } = cfg;

    // prettier-ignore
    return switchMap(([dsc, params, idx]) => {
        const { contents_url } = dsc;
        return of([contents_url, params, idx]).pipe(
            tag("ajaxLoadInputs"), 
            loadDscContent({ windowSize })
        );
    });
};
