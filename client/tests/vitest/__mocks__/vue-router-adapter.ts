/**
 * Vue Router Compatibility Adapter
 *
 * Provides both Vue Router 3 (default export, VueRouter constructor) and
 * Vue Router 4 (named exports, createRouter) APIs for test compatibility.
 */
// Import from actual path to avoid circular alias resolution
// @ts-ignore
import * as VueRouterOriginal from "../../../node_modules/vue-router/dist/vue-router.mjs";

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
    RouterLink,
    RouterView,
    onBeforeRouteLeave,
    onBeforeRouteUpdate,
    isNavigationFailure,
    NavigationFailureType,
    START_LOCATION,
    createWebHashHistory,
};

export const createRouter = _createRouter;
export const createWebHistory = _createWebHistory;
export const createMemoryHistory = _createMemoryHistory;
export const useRoute = _useRoute;
export const useRouter = _useRouter;

/**
 * Vue Router 3 compatibility - VueRouter constructor
 *
 * This creates a class that mimics Vue Router 3's VueRouter constructor
 * but actually uses Vue Router 4's createRouter under the hood.
 */
class VueRouterCompat {
    private router: Router;

    constructor(options: any = {}) {
        const routes = options.routes || [];
        const history = _createMemoryHistory();

        this.router = _createRouter({
            history,
            routes,
        });
    }

    // Proxy all router methods
    push(...args: any[]) {
        return this.router.push(...args);
    }

    replace(...args: any[]) {
        return this.router.replace(...args);
    }

    go(delta: number) {
        return this.router.go(delta);
    }

    back() {
        return this.router.back();
    }

    forward() {
        return this.router.forward();
    }

    beforeEach(guard: any) {
        return this.router.beforeEach(guard);
    }

    afterEach(guard: any) {
        return this.router.afterEach(guard);
    }

    resolve(to: any, current?: any) {
        return this.router.resolve(to);
    }

    get currentRoute() {
        return this.router.currentRoute;
    }

    // Vue Router 3 install method (for localVue.use(VueRouter))
    static install(app: any) {
        // No-op for compatibility - Vue Router 4 uses plugin pattern
    }

    // Instance install for app.use(routerInstance)
    install(app: any) {
        return this.router.install(app);
    }

    // Make it usable as a plugin
    get options() {
        return this.router.options;
    }

    isReady() {
        return this.router.isReady();
    }
}

// Default export for Vue Router 3 style: import VueRouter from 'vue-router'
export default VueRouterCompat;

// Also export as named export for explicit imports
export { VueRouterCompat as VueRouter };
