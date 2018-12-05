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

import { setGalaxyInstance } from "app";
import { prependInitialization, initializations$, clearQueue } from "./initQueue";
import { config$ } from "./config";
import { serverPath } from "utils/serverPath";

import { monitorInit } from "utils/installMonitor";
import { initSentry } from "./initSentry";
import { initFormInputAutoFocus } from "./initFormInputAutoFocus";
import { adjustToolTips } from "./adjustToolTips";
import { adjustIframeLinks, addIframeClass } from "./iframesAreTerrible";
import { init_refresh_on_change } from "./refresh_on_change";
import { initPopupMenus } from "./initPopupMenus";
import { initTour } from "./initTour";
import { initWebhooks } from "./initWebhooks";
import { replace_big_select_inputs } from "./replace_big_select_inputs";

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
    console.log("standardInit", label, serverPath());

    // register motley assortment of random and poorly-written javascript inits
    // which were transplanted from python templates
    registerGalaxyInitializations();

    // wait for config to stop changing, then initiate an app
    let galaxy$ = config$.pipe(
        map(cfg => {
            let instance = appFactory(cfg, label);
            return instance;
        })
    );

    // once config, app and initialization array are ready do the init functions
    combineLatest(config$, galaxy$, initializations$).subscribe(([config, galaxy, inits]) => {
        console.group(`runInitializations`, label, serverPath());
        inits.forEach(fn => fn(galaxy, config));
        clearQueue();
        console.groupEnd();
    });
}

/**
 * Most of the time, all we do is launch a GalaxyApp with the passed configs
 *
 * @param {string} label
 * @returns {function} Returns a function that accepts the application
 * configuration and returns a galaxy instance.
 */
const defaultAppFactory = (config, label = "Galaxy") => {
    return setGalaxyInstance(GalaxyApp => {
        let { options, bootstrapped } = config;
        let app = new GalaxyApp(options, bootstrapped);
        app.debug(`${label} app`);
        return app;
    });
};

/**
 * This is the standard load-out of random javascripts that were rendered in the
 * python templats. Add more by using the addInitialization in a specialized
 * endpoint (see admin or analysis entry points for examples)
 *
 * Or directly from a python template by using:
 *    config.addInitialiation(function (galaxy, config) { // your init } )
 */
export function registerGalaxyInitializations() {
    prependInitialization(
        monitorInit,
        addIframeClass,
        initSentry,
        initFormInputAutoFocus,
        adjustToolTips,
        adjustIframeLinks,
        init_refresh_on_change,
        () => replace_big_select_inputs(20, 1500),
        initPopupMenus,
        initTour,
        initWebhooks
    );
}
