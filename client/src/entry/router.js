// A VueRouter tailored to Galaxy entry points.
// Currently:
// - Provides interaction with getAppRoot to implicitly supply base.
// - Adds declarative masthead logic.
// - Handles confirmation logic in locations with confirmation set.
// - Emits router-push event to app.
// - Avoids console warning on NavigationDuplicated events.

import Vue from "vue";
import VueRouter from "vue-router";
import { getAppRoot } from "onload/loadConfig";

Vue.use(VueRouter);

// patches $router.push() to trigger an event and hide duplication warnings
const originalPush = VueRouter.prototype.push;
VueRouter.prototype.push = function push(location) {
    // verify if confirmation is required
    console.debug("VueRouter - push: ", location);
    if (this.confirmation) {
        if (confirm("There are unsaved changes which will be lost.")) {
            this.confirmation = undefined;
        } else {
            return;
        }
    }
    // always emit event when a route is pushed
    this.app.$emit("router-push");
    // avoid console warning when user clicks to revisit same route
    return originalPush.call(this, location).catch((err) => {
        if (err.name !== "NavigationDuplicated") {
            throw err;
        }
    });
};

export function getGalaxyRouter(routerOptions, mastheadOptions = null) {
    routerOptions.base = routerOptions.base || getAppRoot();

    function storeGalaxyOptionsToMetaOnArray(definesRoutes, defaultMastheadOptions = null) {
        for (const definesRoute of definesRoutes || []) {
            storeGalaxyOptionsToMeta(definesRoute, defaultMastheadOptions);
        }
    }

    function storeGalaxyOptionsToMeta(definesRoute, defaultMastheadOptions = null) {
        definesRoute = definesRoute || [];
        if (definesRoute.masthead || defaultMastheadOptions) {
            console.log("in here with masthead options...");
            definesRoute.meta = definesRoute.meta || {};
            definesRoute.meta.masthead = definesRoute.masthead || defaultMastheadOptions;
        }
        storeGalaxyOptionsToMetaOnArray(definesRoute.children, definesRoute.masthead);
    }

    storeGalaxyOptionsToMetaOnArray(routerOptions.routes);

    const router = new VueRouter(routerOptions);
    if (mastheadOptions) {
        router.beforeEach((to, from, next) => {
            mastheadOptions.reset();
            for (const [key, value] of Object.entries(to.meta?.masthead || {})) {
                if (key in mastheadOptions.$data) {
                    Vue.set(mastheadOptions, key, value);
                } else {
                    console.warn(`Unknown masthead option ${key} encountered in route`);
                }
            }
            next();
        });
    }
    return router;
}
