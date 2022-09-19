// Sync Galaxy store to legacy galaxy current user

import { pluck, switchMap } from "rxjs/operators";
import { monitorBackboneModel } from "utils/observable";

export function syncUserToGalaxy(galaxy$, store) {
    const result$ = galaxy$.pipe(
        // Galaxy.user
        pluck("user"),
        // use backbone change event to monitor current user
        switchMap((model) => monitorBackboneModel(model))
    );

    return result$.subscribe(
        (user) => store.commit("user/setCurrentUser", user),
        (err) => console.log("syncUserToGalaxy error", err),
        () => console.log("syncUserToGalaxy complete")
    );
}
