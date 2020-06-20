// Bootstrap overwrites .tooltip() method, load it after jquery-ui
// (which is loaded everywhere via libs/jquery.custom.js)
import "bootstrap";
import "bootstrap-tour";

// Galaxy core styles
import "scss/base.scss";

// Set dynamically loaded webpack public path.
// This is, by default, just `/static/dist`, but if galaxy is being served at a
// prefix (e.g.  `<server>/galaxy/`), this must happen before any dynamic
// bundle imports load, otherwise they will fail.
import { getRootFromIndexLink } from "./getRootFromIndexLink";
__webpack_public_path__ = `${getRootFromIndexLink().replace(/\/+$/, "")}/${__webpack_public_path__.replace(
    /^\/+/,
    ""
)}`;

// Module exports appear as objects on window.config in the browser
export { standardInit } from "./standardInit";
export { initializations$, addInitialization, prependInitialization, clearInitQueue } from "./initQueue";
export { config$, set as setConfig, get as getConfig, getAppRoot } from "./loadConfig";
export { getRootFromIndexLink } from "./getRootFromIndexLink";

// Client-side configuration variables (based on environment)
import config from "config";
console.log("Configs:", config.name, config);
