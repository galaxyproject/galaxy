import { pipe, defer, of } from "rxjs";
import { repeat, switchMap, catchError } from "rxjs/operators";
import { tag } from "rxjs-spy/operators/tag";
import { decay } from "../../../../utils/observable/decay";
import { loadHistoryContents } from "../../caching";

// prettier-ignore
export const loadContents = (cfg = {}) => {
    const {
        windowSize,
        initialInterval = 3 * 1000,
        maxInterval = 10 * initialInterval,
        disablePoll = false,
    } = cfg;

    return pipe(
        switchMap(([{id}, params, hid]) => {
            const singleLoad$ = defer(() => of([id, params, hid]).pipe(
                tag('ajaxLoadInputs'),
                loadHistoryContents({ windowSize }),
            ));
            const poll$ = singleLoad$.pipe(
                decay({ initialInterval, maxInterval }),
                repeat(),
            );
            return disablePoll ? singleLoad$ : poll$;
        }),
        catchError(err => {
            console.warn("Error in loadContents", err);
            throw err;
        })
    );
}
