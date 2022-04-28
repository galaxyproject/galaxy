/**
 * This is a collection of miscellaneous javascripts that that were previously
 * printed to the page by python templates or just floating around the onload.js
 * file.
 *
 * One day soon, these will all disappear because any functionality they provide
 * will more properly be run inside a lifecycle handler inside of a component.
 */

import { prependInitialization } from "../initQueue";

// specific initialization functions
import { monitorInit } from "utils/installMonitor";
import { initSentry } from "./initSentry";
import { initTooltips } from "./initTooltips";
import { adjustIframeLinks, addIframeClass } from "./iframesAreTerrible";
import { init_refresh_on_change } from "./init_refresh_on_change";
import { onloadWebhooks } from "./onloadWebhooks";
import { replace_big_select_inputs } from "./replace_big_select_inputs";
import { make_popup_menus } from "ui/popupmenu";
import { initModals } from "./initModals";

export function globalInits() {
    prependInitialization(
        monitorInit,
        initSentry,
        addIframeClass,
        adjustIframeLinks,
        initModals,
        initTooltips,
        init_refresh_on_change,
        () => replace_big_select_inputs(20, 1500),
        make_popup_menus,
        onloadWebhooks
    );
}
