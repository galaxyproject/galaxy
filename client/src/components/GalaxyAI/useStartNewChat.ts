import { useRoute, useRouter } from "vue-router/composables";

import { useChatStore } from "@/stores/chatStore";

/** Shared behavior for the various "New Chat" buttons. */
export function useStartNewChat() {
    const route = useRoute();
    const router = useRouter();
    const chatStore = useChatStore();

    /** @param center whether the fresh conversation should open in the center view */
    return function startNewChat(center: boolean) {
        if (center) {
            if (route.path !== "/galaxyai/new") {
                router.push("/galaxyai/new");
            }
        } else {
            // make sure the docked/bottom panel is visible
            chatStore.showChat();
        }
        // Reset via the store, not just the route/id above: for an unsaved
        // conversation the identity wouldn't change, so a plain navigation or
        // showChat(null) is a no-op.
        chatStore.requestNewChat();
    };
}
