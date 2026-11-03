import type { Decorator } from "@storybook/vue3-vite";
import { h } from "vue";

import type { AnyUser } from "@/api";
import { useUserStore } from "@/stores/userStore";

import { getFakeRegisteredUser } from "./index";

/**
 * Story parameters for who is viewing a story. Set it per story, not in the meta: Storybook merges
 * object parameters deeply, so a story's user would mix with the meta's. A stories file's usual
 * viewer goes in `withCurrentUser` instead.
 */
export function viewedBy(user: AnyUser) {
    return { currentUser: user };
}

/**
 * Puts the story's `viewedBy` user, or else a fresh `defaultUser()`, in the user store, as the app
 * does after loading it.
 */
export function withCurrentUser(defaultUser: () => AnyUser = () => getFakeRegisteredUser()): Decorator {
    return (story, { parameters }) => ({
        setup() {
            useUserStore().currentUser = parameters.currentUser ?? defaultUser();
        },
        render: () => h(story()),
    });
}
