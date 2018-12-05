/**
 * This module is full of miscellaneous global initializations that should be
 * more properly assigned to the views that need this functionality. There are
 * very few truly global features in here but most of this folder should
 * disappear as we replace the existing parts with self-initializing components.
 */

// Bootstrap overwrites .tooltip() method, so load it after jquery-ui
import "bootstrap";
import "bootstrap-tour";

// Global galaxy core styles
import "scss/base.scss";

// config access utilities
export { getConfig, getAppRoot, setConfig, config$ } from "./config";

// allows specific endpoints to modify the initialization chain as necessary
export { addInitialization, prependInitialization } from "./initQueue";

// The actual page init function (previously onload.js)
export { standardInit } from "./standardInit";
