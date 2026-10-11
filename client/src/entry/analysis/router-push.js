import { getGalaxyInstance } from "@/app";
import { eventBus } from "@/utils/eventBus";
import { addSearchParams } from "@/utils/url";

/**
 * Resolves a location to its full path without the router base. vue-router 4
 * drops a query embedded in an object's `path`, so that one is resolved
 * as a string and merged with any `query` passed alongside it.
 */
function resolveFullPath(router, location) {
    if (typeof location === "string") {
        return location;
    }
    if (location.path?.includes("?")) {
        const { path, ...rest } = location;
        const fromPath = router.resolve(path);
        return router.resolve({ ...rest, path: fromPath.path, query: { ...fromPath.query, ...rest.query } }).fullPath;
    }
    return router.resolve(location).fullPath;
}

/**
 * Is called before the regular router.push() and allows us to provide logs,
 * handle the window manager, and force a component refresh if needed.
 *
 * Unsaved-change confirmation is handled by the router's beforeEach guard, and
 * vue-router 4 resolves duplicate navigations instead of rejecting them.
 *
 * @param {Object} router instance returned by createRouter()
 */
export function patchRouterPush(router) {
    const originalPush = router.push.bind(router);
    /**
     * @param {String|Object} location as passed to the original router.push()
     * @param {Object} options to provide a title, force reload, and/or prevent window manager
     */
    router.push = function push(location, options = {}) {
        // add key to location to force component refresh
        const { title, force, preventWindowManager } = options;
        if (force) {
            // fullPath excludes the router base, so it is safe to push back as a string
            location = addSearchParams(resolveFullPath(router, location), { __vkey__: Date.now() });
        }
        // show location in window manager
        const Galaxy = getGalaxyInstance();
        if (title && !preventWindowManager && Galaxy?.frame?.active) {
            Galaxy.frame.add({ title: title, url: location });
            return;
        }
        // always emit event, even when a duplicate route is pushed
        eventBus.emit("router-push");
        return originalPush(location);
    };
}
