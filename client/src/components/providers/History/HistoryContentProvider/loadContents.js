import { defer, of, throwError } from "rxjs";
import { switchMap, debounceTime, startWith, repeatWhen } from "rxjs/operators";
import { decay } from "utils/observable";
import { monitorXHR } from "utils/observable/monitorXHR";
import { loadHistoryContents } from "components/providers/History/caching";
import { SearchParams } from "components/providers/History/SearchParams";

// prettier-ignore
export const loadContents = (cfg = {}) => {
    const {
        history,
        filters,
        initialInterval = 2 * 1000,
        maxInterval = 10 * initialInterval,
        disablePoll = false,
        debug = false,
        windowSize = 2 * SearchParams.pageSize,
    } = cfg;

    if (history === undefined) {
        return throwError(new Error("Missing history in loadContents"));
    }
    if (filters === undefined) {
        return throwError(new Error("Missing filters in loadContents"));
    }

    const { id } = history;

    const singleLoad = (hid) => defer(() => of([id, filters, hid]).pipe(
        loadHistoryContents({ windowSize }),
    ));

    const poll = (request$) => resetPoll(100).pipe(
        switchMap(() => request$.pipe(
            repeatWhen(completed$ => completed$.pipe(
                decay({ initialInterval, maxInterval, debug }),
            ))
        ))
    );

    return switchMap((hid) => {
        const request$ = singleLoad(hid);
        return disablePoll ? request$ : poll(request$);
    })
};

// history, tools routes all refresh
// prettier-ignore
const resetPoll = (debouncePeriod) => {
    const routes = [/api\/(history|tools|histories)/];
    const methods = ["POST", "PUT", "DELETE"];

    return monitorXHR({ methods, routes }).pipe(
        startWith(true), 
        debounceTime(debouncePeriod)
    );
};
