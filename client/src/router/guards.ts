import type { NavigationGuardNext, Route } from "vue-router";

import { useUserStore } from "@/stores/userStore";

export async function requireAuth(to: Route, from: Route, next: NavigationGuardNext) {
    const userStore = useUserStore();
    await userStore.loadUser(false);

    if (userStore.isAnonymous) {
        next({
            path: "/login/start",
            query: {
                redirect: to.fullPath,
            },
        });
        return;
    }
    next();
}
