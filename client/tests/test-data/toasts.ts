import { GToast } from "@galaxyproject/galaxy-ui";
import type { Decorator } from "@storybook/vue3-vite";
import { h, onUnmounted } from "vue";

import { useToast } from "@/composables/toast";

/** Name of the region `withToasts` shows toasts in; plays find them within it. */
export const NOTIFICATIONS = "Notifications";

/**
 * The app shell's toast stack beside the story, in a region named `NOTIFICATIONS` so a toast
 * (role `alert`) isn't confused with the story's own alerts. Removes only the toasts
 * created while the story was mounted.
 */
export const withToasts: Decorator = (story) => ({
    setup() {
        const toast = useToast();
        const existingToastIds = new Set(toast.toasts.value.map((item) => item.id));
        onUnmounted(() => {
            for (const item of [...toast.toasts.value]) {
                if (!existingToastIds.has(item.id)) {
                    toast.removeToast(item.id);
                }
            }
        });
    },
    render: () => h("div", [h(story()), h("section", { "aria-label": NOTIFICATIONS }, [h(GToast)])]),
});
