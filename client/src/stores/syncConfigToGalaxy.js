import { map, pluck } from "rxjs/operators";

import { useConfigStore } from "@/stores/configurationStore";

export function syncConfigToGalaxy(galaxy$) {
    const cfg$ = galaxy$.pipe(
        pluck("config"),
        // make sure we're not operating on that config by reference.
        // we want a unique copy to stick into Vuex
        map((config) => Object.assign({}, config))
    );

    return cfg$.subscribe(
        (cfg) => {
            const configStore = useConfigStore();
            configStore.setConfiguration(cfg);
        },
        (err) => console.log("syncConfigToGalaxy error", err),
        () => console.log("syncConfigToGalaxy complete")
    );
}
