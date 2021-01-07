// Sync Galaxy store to legacy galaxy current history

import { getGalaxyInstance } from "app";
import { switchMap, pluck } from "rxjs/operators";
import { monitorChange } from "utils/observable/monitorChange";
import { monitorBackboneModel } from "utils/observable/monitorBackboneModel";

// prettier-ignore
export function syncCurrentHistoryToGalaxy(handler) {

    // wait for the current history panel to appear
    const currentHistoryPanel$ = monitorChange(() => {
        return getGalaxyInstance()?.currHistoryPanel?.model;
    });

    // then emit the id each time it changes
    const result$ = currentHistoryPanel$.pipe(
        switchMap(model => monitorBackboneModel(model, "id").pipe(
            pluck("id")
        ))
    );

    return result$.subscribe(
        val => handler(val),
        err => console.log("syncCurrentHistoryToGalaxy error", err),
        () => console.log("syncCurrentHistoryToGalaxy complete")
    );
}
