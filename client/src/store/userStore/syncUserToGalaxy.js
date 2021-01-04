// Sync Galaxy store to legacy galaxy current user

import { getGalaxyInstance } from "app";
import { switchMap } from "rxjs/operators";
import { monitorChange } from "utils/observable/monitorChange";
import { monitorBackboneModel } from "utils/observable/monitorBackboneModel";

// prettier-ignore
export function syncUserToGalaxy(handler) {

    // wait for galaxy.user to appear
    const user$ = monitorChange(() => {
        return getGalaxyInstance()?.user;
    });

    // then every time the id changes, emit
    const result$ = user$.pipe(
        switchMap(model => monitorBackboneModel(model, "id"))
    );

    return result$.subscribe(
        val => handler(val),
        err => console.log("syncUserToGalaxy error", err),
        () => console.log("syncUserToGalaxy complete")
    );
}
