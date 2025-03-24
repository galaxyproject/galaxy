/**
 * Navigation mixin for legacy code. Supplies functions to components
 * to navigation to locations not controlled by Vue.
 */
import { prependPath, redirectToUrl } from "utils/redirect";

// straight ifrme redirect
export function iframeRedirect(path, target = "galaxy_main") {
    try {
        const targetFrame = window.frames[target];
        if (!targetFrame) {
            throw new Error(`请求的框架 ${target} 不存在`);
        }
        targetFrame.location = prependPath(path);
        return true;
    } catch (err) {
        console.warn("iframe重定向失败", err, ...arguments);
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
