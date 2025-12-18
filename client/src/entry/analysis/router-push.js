import { getGalaxyInstance } from "@/app";
import { addSearchParams } from "@/utils/url";

/**
 * Is called before the regular router.push() and allows us to provide logs,
 * handle the window manager, avoid duplication warnings, and force a component
 * refresh if needed.
 *
 * @param {String} Location as parsed to original router.push()
 * @param {Object} Custom options, to provide a title, force reload, and/or prevent window manager
 */
export function patchRouterPush(VueRouter) {
    const originalPush = VueRouter.prototype.push;
    VueRouter.prototype.push = function push(location, options = {}) {
        // add key to location to force component refresh
        const { title, force, preventWindowManager } = options;
        if (force) {
            // since location can either be string or object, we need to pass the string url to addSearchParams
            if (typeof location === "string") {
                location = addSearchParams(location, { __vkey__: Date.now() });
            } else if (typeof location === "object") {
                // convert to string version addSearchParams can handle
                let url = this.resolve(location).href;
                url = addSearchParams(url, { __vkey__: Date.now() });
                // convert back to object version
                location = this.resolve(url).route;
            }
        }
        // verify if confirmation is required
        if (this.confirmation) {
            if (confirm("There are unsaved changes which will be lost.")) {
                this.confirmation = undefined;
            } else {
                return;
            }
        }
        // show location in window manager
        const Galaxy = getGalaxyInstance();
        if (title && !preventWindowManager && Galaxy.frame && Galaxy.frame.active) {
            Galaxy.frame.add({ title: title, url: location });
            return;
        }
        // always emit event, even when a duplicate route is pushed
        this.app.$emit("router-push");
        // avoid console warning when user clicks to revisit same route
        return originalPush.call(this, location).catch((err) => {
            if (err.name !== "NavigationDuplicated") {
                throw err;
            }
        });
    };
}
