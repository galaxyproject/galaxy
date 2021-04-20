import { concat, defer, of, throwError } from "rxjs";
import { delay, repeat, switchMap, switchMapTo, debounceTime, startWith } from "rxjs/operators";
import { decay } from "utils/observable";
import { monitorXHR } from "utils/observable/monitorXHR";
import { loadHistoryContents } from "../../caching";
import { SearchParams } from "../../model";

// prettier-ignore
export const loadContents = (cfg = {}) => {
    const {
        history,
        filters,
        initialInterval = 2 * 1000,
        maxInterval = 10 * initialInterval,
        disablePoll = false,
        // debug = false,
        // time between initial load and polling start
        startingDelay = 5000,
        windowSize = 2 * SearchParams.pageSize,
    } = cfg;

    if (history === undefined) {
        return throwError(new Error("Missing history in loadContents"));
    }
    if (filters === undefined) {
        return throwError(new Error("Missing filters in loadContents"));
    }

    const { id } = history;

    return switchMap((hid) => {

        // a single history update
        const singleLoad$ = of([id, filters, hid]).pipe(
            loadHistoryContents({ windowSize })
        );

        // start repeating, delay gets longer over time until unsubscribed
        const freshPoll$ = defer(() => singleLoad$.pipe(
            decay({ initialInterval, maxInterval }),
            repeat()
        ));

        // history, tools routes all refresh
        // exclude our own polling url though
        const routes = [/api\/(history|tools|histories)/];
        const methods = ["POST", "PUT", "DELETE"];
        const resetPoll$ = monitorXHR({ methods, routes });

        // resets re-subscribe to freshPoll$ starting the decay over again
        const poll$ = resetPoll$.pipe(
            startWith(true),
            debounceTime(100),
            switchMapTo(freshPoll$)
        );

        // if we're polling, add a little delay between initial load and polling
        // avoids pointless polling if the user is rapidly changing the view
        const polling$ = of(true).pipe(
            delay(startingDelay),
            switchMapTo(poll$)
        );

        return disablePoll ? singleLoad$ : concat(singleLoad$, polling$);
    })
};
