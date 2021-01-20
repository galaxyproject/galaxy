import { defer, of } from "rxjs";
import { repeat, switchMap, switchMapTo, startWith, debounceTime } from "rxjs/operators";
import { decay } from "utils/observable/decay";
import { monitorXHR } from "utils/observable/monitorXHR";
import { loadHistoryContents } from "../../caching";

// prettier-ignore
export const loadContents = (cfg = {}) => {
    const { 
        windowSize, 
        initialInterval = 2 * 1000, 
        maxInterval = 10 * initialInterval, 
        disablePoll = false 
    } = cfg;

    return switchMap(([{ id }, params, hid]) => {

        // a single history update
        const singleLoad$ = of([id, params, hid]).pipe(
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

        return disablePoll ? singleLoad$ : poll$;
    });
};
