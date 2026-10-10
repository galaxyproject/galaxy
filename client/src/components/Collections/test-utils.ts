import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

/** Clicks one of `CreatorWithHistory`'s buttons, as a history poll reporting that change. */
export async function changeHistory(wrapper: VueWrapper, label: string) {
    const button = wrapper.findAll("fieldset button").find((candidate) => candidate.text() === label);
    if (!button) {
        throw new Error(`No history control "${label}"`);
    }
    await button.trigger("click");
    await flushPromises();
}
