import type { RouteLocationNormalized, RouteLocationRaw } from "vue-router";

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
 * trip through login even when the user turns out to be signed in already. It has to be
 * root-relative: the router applies `base` itself, so a destination that already carries
 * the app root would end up with it twice.
 *
 * This is a navigation guard rather than a route-level `redirect`, because vue-router
 * treats a `redirect` function returning undefined as "no match" and renders nothing --
 * which would leave anonymous users staring at a blank login page.
 */
export function redirectLoggedIn(to: RouteLocationNormalized) {
    const Galaxy = getGalaxyInstance();
    if (!Galaxy?.user?.id) {
        return;
    }
    const redirect = safeRedirectPath(to.query.redirect);
    return redirect && !LOGIN_ENTRY_ROUTES.includes(redirect) ? redirect : "/";
}

async function anonymousRedirect(to: RouteLocationNormalized): Promise<RouteLocationRaw | undefined> {
    const userStore = useUserStore();
    await userStore.loadUser(false);

    if (userStore.isAnonymous) {
        return {
            path: "/login/start",
            query: { redirect: to.fullPath },
        };
    }
    return undefined;
}

export async function requireAuth(to: RouteLocationNormalized) {
    return await anonymousRedirect(to);
}

export async function requireAuthForUploadMethod(to: RouteLocationNormalized) {
    const methodId = to.params.methodId as UploadMethod;
    const method = getUploadMethod(methodId);

    if (!method) {
        return { path: "/upload", replace: true };
    }

    if (method.requiresLogin) {
        return await anonymousRedirect(to);
    }
}
