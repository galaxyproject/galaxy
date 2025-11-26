/**
 * jQuery custom build for Vite
 * ESM-compatible version that exposes jQuery globally
 */

import jQuery from "jquery";
import "jquery-migrate";

// Expose jQuery globally for legacy code
if (typeof window !== "undefined") {
    window.$ = window.jQuery = jQuery;
}

export default jQuery;
export { jQuery };
