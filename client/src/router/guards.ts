import type { RouteLocationNormalized } from "vue-router";

import { useUserStore } from "@/stores/userStore";

export async function requireAuth(to: RouteLocationNormalized) {
    const userStore = useUserStore();
    await userStore.loadUser(false);

    if (userStore.isAnonymous) {
        return {
            path: "/login/start",
            query: {
                redirect: to.fullPath,
            },
        };
    }
}
