// Sync Galaxy store to legacy galaxy current history

import { switchMap, pluck, shareReplay, filter, distinctUntilChanged } from "rxjs/operators";
import { monitorBackboneModel } from "utils/observable/monitorBackboneModel";

export function syncCurrentHistoryToGalaxy(galaxy$, store) {
    const historyId$ = galaxy$.pipe(
        pluck("currHistoryPanel", "model"),
        filter(Boolean),
        switchMap((model) => monitorBackboneModel(model).pipe(shareReplay(1))),
        pluck("id"),
        distinctUntilChanged()
    );

    return historyId$.subscribe(
        (id) => {
            console.log("subscription id", id);
            store.commit("betaHistory/setCurrentHistoryId", id);
        },
        (err) => console.log("syncCurrentHistoryToGalaxy error", err),
        () => console.log("syncCurrentHistoryToGalaxy complete")
    );
}
