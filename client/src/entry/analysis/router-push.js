import { getGalaxyInstance } from "app";
import { addSearchParams } from "utils/url";

/**
 * Is called before the regular router.push() and allows us to provide logs,
 * handle the window manager, avoid duplication warnings, and force a component
 * refresh if needed.
 *
 * @param {String} Location as parsed to original router.push()
 * @param {Object} Custom options, to provide a title and/or force reload
 */
export function patchRouterPush(VueRouter) {
    const originalPush = VueRouter.prototype.push;
    VueRouter.prototype.push = function push(location, options = {}) {
        // add key to location to force component refresh
        const { title, force } = options;
        if (force) {
            location = addSearchParams(location, { __vkey__: Date.now() });
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
        if (title && Galaxy.frame && Galaxy.frame.active) {
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
