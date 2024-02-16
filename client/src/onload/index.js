// Bootstrap overwrites .tooltip() method, load it after jquery-ui
// (which is loaded everywhere via libs/jquery.custom.js)
import "bootstrap";
// Galaxy core styles
import "scss/base.scss";
// Set up webpack's public path; nothing to import but the module has side
// effects fixing webpack globals.
import "./publicPath";
// Default Font
import "@fontsource/atkinson-hyperlegible";
import "@fontsource/atkinson-hyperlegible/700.css";

// Client-side configuration variables (based on environment)
import { library } from "@fortawesome/fontawesome-svg-core";
import config from "config";

// Custom Icons
import customIconPack from "@/assets/icons.json";

import { overrideProductionConsole } from "./console";

overrideProductionConsole();

// Module exports appear as objects on window.config in the browser
export { getRootFromIndexLink } from "./getRootFromIndexLink";
export { addInitialization, clearInitQueue, initializations$, prependInitialization } from "./initQueue";
export { config$, getAppRoot, get as getConfig, set as setConfig } from "./loadConfig";
export { standardInit } from "./standardInit";

if (!config.testBuild === true) {
    console.log(`Galaxy Client '${config.name}' build, dated ${config.buildTimestamp}`);
    console.debug("Full configuration:", config);
}

library.add(customIconPack);
