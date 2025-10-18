/**
 * This is a collection of miscellaneous javascripts that that were previously
 * printed to the page by python templates or just floating around the onload.js
 * file.
 *
 * One day soon, these will all disappear because any functionality they provide
 * will more properly be run inside a lifecycle handler inside of a component.
 */

import { monitorInit } from "utils/installMonitor";

import { prependInitialization } from "../initQueue";
import { initSentry } from "./initSentry";
import { onloadWebhooks } from "./onloadWebhooks";

export function globalInits() {
    prependInitialization(monitorInit, initSentry, onloadWebhooks);
}
