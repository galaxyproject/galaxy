import type { NavigationGuardNext, Route } from "vue-router";

import { getGalaxyInstance } from "@/app";
import type { UploadMethod } from "@/components/Panels/Upload/types";
import { getUploadMethod } from "@/components/Panels/Upload/uploadMethodRegistry";
import { useUserStore } from "@/stores/userStore";
import { safeRedirectPath } from "@/utils/redirect";

// Entry routes that exist to get you logged in -- never a destination to come back to.
const LOGIN_ENTRY_ROUTES = ["/login/start", "/register/start"];

/**
 * Keeps logged-in users off the login and registration entry routes.
 *
 * A pending `redirect` is honored rather than dropped, so a deep link survives the round
 * trip through login even when the user turns out to be signed in already.
 *
 * This is a navigation guard rather than a route-level `redirect`, because vue-router
 * treats a `redirect` function returning undefined as "no match" and renders nothing --
 * which would leave anonymous users staring at a blank login page.
 */
export function redirectLoggedIn(to: Route, _from: Route, next: NavigationGuardNext) {
    const Galaxy = getGalaxyInstance();
    if (!Galaxy?.user?.id) {
        next();
        return;
    }
    const redirect = safeRedirectPath(to.query.redirect);
    next(redirect && !LOGIN_ENTRY_ROUTES.includes(redirect) ? redirect : "/");
}

async function redirectIfAnonymous(to: Route, next: NavigationGuardNext) {
    const userStore = useUserStore();
    await userStore.loadUser(false);

    if (userStore.isAnonymous) {
        next({
            path: "/login/start",
            query: { redirect: to.fullPath },
        });
        return true;
    }
    return false;
}

export async function requireAuth(to: Route, _from: Route, next: NavigationGuardNext) {
    if (await redirectIfAnonymous(to, next)) {
        return;
    }
    next();
}

export async function requireAuthForUploadMethod(to: Route, _from: Route, next: NavigationGuardNext) {
    const methodId = to.params.methodId as UploadMethod;
    const method = getUploadMethod(methodId);

    if (method?.requiresLogin && (await redirectIfAnonymous(to, next))) {
        return;
    }
    next();
}
