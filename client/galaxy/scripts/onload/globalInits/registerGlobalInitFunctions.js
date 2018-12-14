/**
 * This is a collection of miscellaneous javascripts that that were previously
 * printed to the page by python templates. Add more by using the
 * addInitialization in a specialized endpoint (see admin or analysis entry
 * points for examples).
 *
 * Or directly from a python template by using:
 *    config.addInitialiation(function (galaxy, config) { // your init } )
 * 
 * One day soon, these will all disappear because any functionality they provide
 * will more properly be run inside a lifecycle handler inside of a component.
 */

import { prependInitialization } from "./initQueue";

// specific initialization functions functions
import { monitorInit } from "utils/installMonitor";
import { initSentry } from "./initSentry";
// import { initFormInputAutoFocus } from "./initFormInputAutoFocus";
// import { adjustToolTips } from "./adjustToolTips";
// import { adjustIframeLinks, addIframeClass } from "./iframesAreTerrible";
// import { init_refresh_on_change } from "./refresh_on_change";
// import { initPopupMenus } from "./initPopupMenus";
// import { initTour } from "./initTour";
// import { initWebhooks } from "./initWebhooks";
// import { replace_big_select_inputs } from "./replace_big_select_inputs";

export function registerGlobalInitFunctions() {
    prependInitialization(
        monitorInit,
        // addIframeClass,
        initSentry,
        // initFormInputAutoFocus,
        // adjustToolTips,
        // adjustIframeLinks,
        // init_refresh_on_change,
        // () => replace_big_select_inputs(20, 1500),
        // initPopupMenus,
        // initTour,
        // initWebhooks
    );
}