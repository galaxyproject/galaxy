/**
 * Watches for key changes in global Galaxy app variable and transfers them into Vuex via commits.
 * This should be deleted when Galaxy is finally done, as features get moved into Vuex individual
 * sync functions can be removed from the plugin
 */

import { getGalaxyInstance } from "app";
import { defer } from "rxjs";
import { shareReplay } from "rxjs/operators";
import { waitForInit } from "utils/observable";

import { syncUserToGalaxy } from "@/stores/users/syncUserToGalaxy";

// store subscriptions

export const syncVuextoGalaxy = (store) => {
    const globalGalaxy$ = defer(() => {
        return waitForInit(() => getGalaxyInstance()).pipe(shareReplay(1));
    });

    // sets current user when galaxy changes
    syncUserToGalaxy(globalGalaxy$);
};
