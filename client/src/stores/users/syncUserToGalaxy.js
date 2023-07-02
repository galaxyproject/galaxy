// Sync Galaxy store to legacy galaxy current user
import { pluck, switchMap } from "rxjs/operators";
import { useUserStore } from "stores/userStore";
import { monitorBackboneModel } from "utils/observable";

export function syncUserToGalaxy(galaxy$) {
    const result$ = galaxy$.pipe(
        // Galaxy.user
        pluck("user"),
        // use backbone change event to monitor current user
        switchMap((model) => monitorBackboneModel(model))
    );

    return result$.subscribe(
        (user) => {
            const userStore = useUserStore();
            userStore?.setCurrentUser(user);
        },
        (err) => console.log("syncUserToGalaxy error", err),
        () => console.log("syncUserToGalaxy complete")
    );
}
