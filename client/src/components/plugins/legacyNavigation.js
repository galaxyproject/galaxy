/**
 * Navigation mixin for legacy code. Supplies functions to components
 * to navigation to locations not controlled by Vue.
 */

import { getGalaxyInstance } from "app";
import { redirectToUrl, prependPath } from "utils/redirect";
import _l from "utils/localization";

// wrapper for backbone router
export function backboneRoute(path, ...args) {
    try {
        getGalaxyInstance().router.push(path, ...args);
    } catch (err) {
        console.warn("Failed galaxy route change", err, ...arguments);
        throw err;
    }
}

// wrapper for window manager
export function iframeAdd({ path, title = "Galaxy", tryIframe = true }) {
    const Galaxy = getGalaxyInstance();
    if (Galaxy.frame && Galaxy.frame.active) {
        Galaxy.frame.add({
            title: _l(title),
            url: prependPath(path),
        });
        return true;
    } else if (tryIframe) {
        return iframeRedirect(path);
    } else {
        return false;
    }
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

// arbitrary Galaxy wrapper
export function useGalaxy(fn) {
    return fn(getGalaxyInstance());
}

// wrapper for navigation to be used as mixin
export const legacyNavigationMixin = {
    methods: {
        redirect,
        iframeAdd,
        iframeRedirect,
        backboneRoute,
        useGalaxy,
        prependPath,
    },
};

// wrapper for navigation to be used as plugin
export const legacyNavigationPlugin = {
    install(Vue) {
        Vue.mixin(legacyNavigationMixin);
    },
};
