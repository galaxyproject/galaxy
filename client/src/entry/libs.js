/**
 * libs.bundled.js entry point
 * This must be loaded BEFORE the app bundles (analysis, generic)
 *
 * It exposes required globals to window for:
 * - jQuery plugins that expect window.$ and window.jQuery
 */

// Buffer polyfill - some dependencies expect Buffer to be globally available
import { Buffer } from "buffer";
// jQuery - import directly from the package
// Note: We import from "jquery" directly, not via jquery.custom.js,
// to avoid code-splitting issues with Rollup/Vite
import jQuery from "jquery";

window.Buffer = Buffer;

// Expose jQuery globally - this must happen before jquery-migrate loads
window.$ = jQuery;
window.jQuery = jQuery;

// jquery-migrate - must be imported AFTER setting window.jQuery
// Using dynamic import to ensure globals are set first
import("jquery-migrate");
