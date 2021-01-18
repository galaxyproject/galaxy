// Sync Galaxy store to legacy galaxy current history

import { fromEvent } from "rxjs";
import { map, filter, switchMap, pluck, distinctUntilChanged, retryWhen, take, delay } from "rxjs/operators";

export function syncCurrentHistoryToGalaxy(galaxy$, store, cfg = {}) {
    const { retryPeriod = 500, retries = 20 } = cfg;

    // prettier-ignore
    const historyId$ = galaxy$.pipe(
        pluck("currHistoryPanel"),
        switchMap((panel) => {
            // relationship between currHistoryPanel and its model is murky, but I don't care, I'm
            // just going to grab the id fresh after every possible event
            return fromEvent(panel, "all").pipe(
                map(() => panel.model.id)
            );
        }),
        retryWhen(err$ => err$.pipe(
            delay(retryPeriod),
            take(retries)
        )),
        filter(Boolean),
        distinctUntilChanged()
    );

    return historyId$.subscribe(
        (id) => {
            store.commit("betaHistory/setCurrentHistoryId", id);
        },
        (err) => console.log("syncCurrentHistoryToGalaxy error", err),
        () => console.log("syncCurrentHistoryToGalaxy complete")
    );
}
