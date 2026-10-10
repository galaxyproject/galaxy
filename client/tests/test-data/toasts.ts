import { GToast } from "@galaxyproject/galaxy-ui";
import type { Decorator } from "@storybook/vue3-vite";
import { expect, waitFor, within } from "storybook/test";
import { h, onUnmounted } from "vue";

import { useToast } from "@/composables/toast";
import { escapeRegExp } from "@/utils/regExp";

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

/**
 * Checks the toasts `withToasts` shows, oldest first, by their whole text: title then message.
 * Checks for none at once, since toasts dismiss themselves after 3s and waiting could outlast one;
 * wait on something visible first.
 */
export async function seeToasts(canvas: ReturnType<typeof within>, toasts: [title: string, message: string][]) {
    const notifications = within(canvas.getByRole("region", { name: NOTIFICATIONS }));
    const count = () => expect(notifications.queryAllByRole("alert")).toHaveLength(toasts.length);
    await (toasts.length ? waitFor(count) : count());
    const shown = notifications.queryAllByRole("alert");
    for (const [index, [title, message]] of toasts.entries()) {
        await expect(shown[index]).toHaveTextContent(new RegExp(`^${escapeRegExp(`${title} ${message}`)}$`));
    }
}
