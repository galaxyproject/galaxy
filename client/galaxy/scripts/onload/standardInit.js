/**
 * Entry point view initialization This is a collection of functions that were
 * jammed together in the old onload.js script. I've added a queue so we can
 * extend the initializations externally without creating a new entry point (at
 * least until these are all components)
 *
 * This code should be considered transitional. Soon we will have a real Vue app
 * and it will control the order of initialization based on individual component
 * needs. For now, we need to organize the random scripts that are being printed
 * to the python templates.
 */

import { combineLatest } from "rxjs";
import { map } from "rxjs/operators";

import { serverPath } from "utils/serverPath";
import { defaultAppFactory } from "./defaultAppFactory";
import { globalInits } from "./globalInits";

// observable configs and init queue
import { config$ } from "./loadConfig";
import { initializations$, clearInitQueue } from "./initQueue";

/**
 * This is the standard endpoint initialization chain. Configs are loaded, the
 * app is instantiated, then a bunch of initialization scripts are run and
 * passed the new app instance and the configuration variables.
 *
 * @param {string} label Logging identifier
 * @param {function} appFactory Override this parameter with a function matching the
 * signature of defaultAppFactory in the event that you require a custom Galaxy
 * application instance.
 */
export function standardInit(label = "Galaxy", appFactory = defaultAppFactory) {
    // register assortment of random javascript inits
    // which were transplanted from python templates
    globalInits();

    // waits for configs to stop changing then instantiates Galaxy
    let galaxy$ = config$.pipe(map(cfg => appFactory(cfg, label)));

    // once config, app and initialization observables have a value then run all
    // the initialization functions, this will keep running new initialization
    // functions even if they are registered super-late because combineLatest
    // will not remake a the existing Galaxy or config objects, it'll just run
    // the new batch of freshly registered init functions
    combineLatest(config$, galaxy$, initializations$).subscribe(([config, galaxy, inits]) => {
        console.groupCollapsed(`runInitializations`, label, serverPath());
        inits.forEach(fn => fn(galaxy, config));
        clearInitQueue();
        console.groupEnd();
    });
}
