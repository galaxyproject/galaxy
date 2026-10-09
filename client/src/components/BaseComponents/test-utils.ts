import type { BaseWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

/**
 * Clicks the enabled confirm-footer button labelled `text` in a mounted GModal within
 * `wrapper`, then flushes promises. Unlike `vm.$emit("ok" | "cancel")`, this goes through
 * the native dialog, so GModal emits `ok` or `cancel` once, as it does for a user.
 */
export async function clickModalButton(wrapper: Pick<BaseWrapper<Node>, "findAll">, text: string) {
    const matches = wrapper.findAll(".g-modal-confirm-buttons button").filter((button) => button.text() === text);
    const [button] = matches;
    if (!button || matches.length > 1) {
        throw new Error(`expected one "${text}" modal button, found ${matches.length}`);
    }
    if (button.attributes("aria-disabled") === "true") {
        throw new Error(`the "${text}" modal button is disabled`);
    }
    await button.trigger("click");
    await flushPromises();
}
