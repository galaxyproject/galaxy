/**
 * Navigation mixin for legacy code. Supplies functions to components
 * to navigation to locations not controlled by Vue.
 */

import { getGalaxyInstance } from "app";
import { redirectToUrl, prependPath } from "utils/redirect";
import _l from "utils/localization";

// wrapper for window manager
export function iframeAdd({ path, title = "Galaxy", $router = null }) {
    $router.push(path);
}

// straight ifrme redirect
export function iframeRedirect(path, target = "galaxy_main") {
    try {
        const targetFrame = window.frames[target];
        if (!targetFrame) {
            throw new Error(`Requested frame ${target} doesn't exist`);
        }
        targetFrame.location = prependPath(path);
        return true;
    } catch (err) {
        console.warn("Failed iframe redirect", err, ...arguments);
        throw err;
    }
}

// straight window.location
export function redirect(path) {
    console.log("legacyNavigation: go", path);
    redirectToUrl(prependPath(path));
}

// wrapper for navigation to be used as mixin
export const legacyNavigationMixin = {
    methods: {
        redirect,
        iframeAdd,
        iframeRedirect,
        prependPath,
    },
};

// wrapper for navigation to be used as plugin
export const legacyNavigationPlugin = {
    install(Vue) {
        Vue.mixin(legacyNavigationMixin);
    },
};
