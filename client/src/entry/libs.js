/**
 * libs.bundled.js entry point
 * This must be loaded BEFORE the app bundles (analysis, generic)
 *
 * It exposes required globals to window for:
 * - Legacy Mako templates that access window.bundleEntries
 * - jQuery plugins that expect window.$ and window.jQuery
 * - Backbone code that expects global underscore
 * - Legacy code that accesses window.config
 */

// Polyfills (for older browser support)
import "core-js/stable";
import "regenerator-runtime/runtime";

// jQuery - expose to window for legacy code
import jQuery from "jquery";
// Underscore - expose to window for Backbone and legacy code
import _ from "underscore";

// bundleEntries - expose to window for Mako templates
import * as bundleEntries from "@/bundleEntries";
// config - expose to window for legacy code
import * as config from "@/onload/loadConfig";

window.$ = window.jQuery = jQuery;
window._ = _;
window.bundleEntries = bundleEntries;
window.config = config;
