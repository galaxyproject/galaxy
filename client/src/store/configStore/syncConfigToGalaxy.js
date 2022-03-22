import { map, pluck } from "rxjs/operators";

export function syncConfigToGalaxy(galaxy$, store) {
    const cfg$ = galaxy$.pipe(
        pluck("config"),
        // make sure we're not operating on that config by reference.
        // we want a unique copy to stick into Vuex
        map((config) => Object.assign({}, config))
    );

    return cfg$.subscribe(
        (cfg) => store.commit("config/setConfigs", cfg),
        (err) => console.log("syncConfigToGalaxy error", err),
        () => console.log("syncConfigToGalaxy complete")
    );
}
