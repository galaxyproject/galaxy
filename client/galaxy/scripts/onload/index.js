// Bootstrap overwrites .tooltip() method, load it after jquery-ui
// (which is loaded everywhere via libs/jquery.custom.js)
import "bootstrap";
import "bootstrap-tour";

// Galaxy core styles
import "scss/base.scss";

// Module exports appear as objects on window.config in the browser
export { standardInit } from "./standardInit";
export { initializations$, addInitialization, prependInitialization, clearInitQueue } from "./initQueue";
export { config$, set as setConfig, get as getConfig, getAppRoot } from "./loadConfig";
export { getRootFromIndexLink } from "./getRootFromIndexLink";
