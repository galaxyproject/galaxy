/**
 * Navigation mixin for legacy code. Supplies functions to components
 * to navigation to locations not controlled by Vue.
 */

import { getGalaxyInstance } from "app";
import { redirectToUrl, prependPath } from "utils/redirect";
import _l from "utils/localization";

export const legacyNavigationMixin = {
    methods: {
        // straight window.location
        redirect(path) {
            console.log("legacyNavigation: go", path);
            redirectToUrl(prependPath(path));
        },

        // weird wrapper for Galaxy's wierd frame navigation
        // checks for existing galaxy frame reference, uses that or
        // loads a brand new document in the iframe
        iframeAdd({ path, title = "Galaxy", tryIframe = true }) {
            const Galaxy = getGalaxyInstance();
            if (Galaxy.frame && Galaxy.frame.active) {
                Galaxy.frame.add({
                    url: prependPath(path),
                    title: _l(title),
                });
                return true;
            } else if (tryIframe) {
                return this.iframeRedirect(path);
            } else {
                return false;
            }
        },

        // straight ifrme redirect
        iframeRedirect(path, target = "galaxy_main") {
            try {
                const targetFrame = window.frames[target];
                if (!targetFrame) throw new Error(`Requested frame ${target} doesn't exist`);
                targetFrame.location = prependPath(path);
                return true;
            } catch (err) {
                console.warn("Failed iframe redirect", err, ...arguments);
                throw err;
            }
        },

        // galaxy router, wrapper for backbone router
        backboneRoute(path, ...args) {
            try {
                getGalaxyInstance().router.push(prependPath(path), ...args);
            } catch (err) {
                console.warn("Failed galaxy route change", err, ...arguments);
                throw err;
            }
        },

        // arbitrary Galaxy wrapper for all that bizarre logic that shouldn't
        // exist but we can't kill yet
        useGalaxy(fn) {
            return fn(getGalaxyInstance());
        },

        // prepend server prefix from configs to a url
        prependPath,
    },
};

export const legacyNavigationPlugin = {
    install(Vue) {
        Vue.mixin(legacyNavigationMixin);
    },
};
