import { concat } from "rxjs";
import { share, take, takeWhile } from "rxjs/operators";
import { getHistoryMonitor } from "./monitors";

export const monitorHistoryUntilTrue = (condition, historyId, monitorEvery = 3000) => {
    // monitorHistory until condition is true, then fetch one last update
    const historyMonitor$ = getHistoryMonitor(historyId, monitorEvery);
    const primaryHistoryMonitor$ = historyMonitor$.pipe(
        takeWhile(() => !condition()),
        share()
    );
    return concat(
        primaryHistoryMonitor$,
        historyMonitor$.pipe(
            // get one more update after invocation is terminal
            take(1)
        )
    );
};
