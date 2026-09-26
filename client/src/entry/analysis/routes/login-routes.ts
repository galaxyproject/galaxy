import { redirectLoggedIn } from "@/router/guards";

import Login from "@/entry/analysis/modules/Login.vue";
import Register from "@/entry/analysis/modules/Register.vue";

/**
 * Entry routes for logging in and registering.
 *
 * These use a `beforeEnter` guard rather than a route-level `redirect`, so that a
 * pending `redirect` query param is honored instead of dropped -- see the guard for why
 * a `redirect` function would not work here.
 */
export default [
    {
        path: "/login/start",
        component: Login,
        beforeEnter: redirectLoggedIn,
    },
    {
        path: "/register/start",
        component: Register,
        beforeEnter: redirectLoggedIn,
    },
];
