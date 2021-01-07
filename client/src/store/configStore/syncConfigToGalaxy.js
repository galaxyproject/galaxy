import { pluck } from "rxjs/operators";

export function syncConfigToGalaxy(galaxy$, store) {
    const cfg$ = galaxy$.pipe(pluck("config"));

    return cfg$.subscribe(
        (cfg) => {
            console.warn("SYNC CONFIG", cfg);
            store.commit("config/setConfigs", cfg);
        },
        (err) => console.log("syncConfigToGalaxy error", err),
        () => console.log("syncConfigToGalaxy complete")
    );
}
