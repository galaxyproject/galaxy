/**
 * libs.bundled.js entry point
 * This must be loaded BEFORE the app bundles (analysis, generic)
 *
 * It exposes required globals to window for:
 * - jQuery plugins that expect window.$ and window.jQuery
 * - Backbone code that expects global underscore
 *
 * NOTE: bundleEntries and config are now set up by the app bundles (analysis/generic)
 * to avoid circular dependency issues with Vite code splitting.
 */

// Backbone - expose globally for legacy code
import Backbone from "backbone";
// Buffer polyfill - some dependencies expect Buffer to be globally available
import { Buffer } from "buffer";
// jQuery - import directly from the package
// Note: We import from "jquery" directly, not via jquery.custom.js,
// to avoid code-splitting issues with Rollup/Vite
import jQuery from "jquery";
// Underscore - expose to window for Backbone and legacy code
import _ from "underscore";

window.Buffer = Buffer;
window._ = _;
window.Backbone = Backbone;

// Expose jQuery globally - this must happen before jquery-migrate loads
window.$ = jQuery;
window.jQuery = jQuery;

// jquery-migrate - must be imported AFTER setting window.jQuery
// Using dynamic import to ensure globals are set first
import("jquery-migrate");
