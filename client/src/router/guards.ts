import type { NavigationGuardNext, Route } from "vue-router";

import type { UploadMethod } from "@/components/Panels/Upload/types";
import { getUploadMethod } from "@/components/Panels/Upload/uploadMethodRegistry";
import { useUserStore } from "@/stores/userStore";

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
