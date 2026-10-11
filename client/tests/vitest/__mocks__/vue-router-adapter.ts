/**
 * Vue Router Compatibility Adapter
 *
 * Provides both Vue Router 3 (default export, VueRouter constructor) and
 * Vue Router 4 (named exports, createRouter) APIs for test compatibility.
 */
// Import the package's Node entry by path; the "vue-router" alias would otherwise resolve back here
// @ts-ignore
import * as VueRouterOriginal from "../../../node_modules/vue-router/vue-router.node.mjs";

const {
    createRouter: _createRouter,
    createWebHistory: _createWebHistory,
    createMemoryHistory: _createMemoryHistory,
    useRoute: _useRoute,
    useRouter: _useRouter,
    RouterLink,
    RouterView,
    onBeforeRouteLeave,
    onBeforeRouteUpdate,
    isNavigationFailure,
    NavigationFailureType,
    START_LOCATION,
    createWebHashHistory,
} = VueRouterOriginal;

// Re-export all Vue Router 4 APIs
export {
    createWebHashHistory,
    isNavigationFailure,
    NavigationFailureType,
    onBeforeRouteLeave,
    onBeforeRouteUpdate,
    RouterLink,
    RouterView,
    START_LOCATION,
};

export const createRouter = _createRouter;
export const createWebHistory = _createWebHistory;
export const createMemoryHistory = _createMemoryHistory;
export const useRoute = _useRoute;
export const useRouter = _useRouter;

/**
 * Vue Router 3 compatibility - VueRouter constructor
 *
 * Mimics Vue Router 3's `new VueRouter(options)` constructor, but hands back
 * the real Vue Router 4 instance instead of a separate wrapper object.
 *
 * Earlier this class held its own `router` and re-implemented push/replace/etc.
 * as proxy methods that delegated to it. That meant `new VueRouter()` returned
 * one object while `app.use(router)` (via `install()`) installed a *different*
 * one (`this.router`), so `$router`/`useRouter()` inside a mounted component
 * resolved to the inner instance. A test that did `router.push = vi.fn()` on
 * the outer wrapper was monkey-patching an object nothing else ever saw --
 * the component's real navigation calls went through the untouched original,
 * so assertions like `expect(router.push).toHaveBeenCalledWith(...)` failed
 * with "is not a spy". Returning the real router directly from the
 * constructor means there is only ever one object, so patching it and
 * installing it both act on the same instance.
 */
class VueRouterCompat {
    constructor(options: any = {}) {
        const routes = options.routes || [];
        const history = _createMemoryHistory();

        // A class constructor that returns an object replaces `this` with
        // that object for `new VueRouterCompat()` -- see MDN's page on the
        // `constructor` method. Vue Router 4's router already implements
        // every instance method/getter Vue Router 3 tests expect (push,
        // replace, go, back, forward, beforeEach, afterEach, resolve,
        // currentRoute, options, isReady, install), so there is nothing left
        // to proxy.
        return _createRouter({
            history,
            routes,
        }) as unknown as VueRouterCompat;
    }

    // Vue Router 3 static install method (for localVue.use(VueRouter))
    static install(_app: any) {
        // No-op for compatibility - Vue Router 4 uses plugin pattern
    }
}

// Default export for Vue Router 3 style: import VueRouter from 'vue-router'
export default VueRouterCompat;

// Also export as named export for explicit imports
export { VueRouterCompat as VueRouter };
