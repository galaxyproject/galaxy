import { composeStories } from "@storybook/vue3-vite";
import { type StoryMountOptions, type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import * as componentStories from "./GDropdownItem.stories";

import GDropdownItem from "./GDropdownItem.vue";

const stories = composeStories(componentStories);
const mountStory = useStoryMount();

/** Click the item and report whether the navigation was cancelled. */
async function clickAndCheckDefaultPrevented(story: StoryOf<typeof stories>, options: StoryMountOptions = {}) {
    const wrapper = mountStory(story, options).getComponent(GDropdownItem);
    const event = new MouseEvent("click", { bubbles: true, cancelable: true });
    wrapper.get("a").element.dispatchEvent(event);
    await nextTick();
    return { wrapper, defaultPrevented: event.defaultPrevented };
}

describe("GDropdownItem.vue", () => {
    it("cancels navigation for action items, which fall back to href='#'", async () => {
        const { wrapper, defaultPrevented } = await clickAndCheckDefaultPrevented(stories.Action);

        expect(wrapper.get("a").attributes("href")).toBe("#");
        expect(defaultPrevented).toBe(true);
        expect(wrapper.emitted("click")).toHaveLength(1);
    });

    it("cancels navigation when href='#' is passed explicitly", async () => {
        const { wrapper, defaultPrevented } = await clickAndCheckDefaultPrevented(stories.Action, {
            props: { href: "#" },
        });

        expect(defaultPrevented).toBe(true);
        expect(wrapper.emitted("click")).toHaveLength(1);
    });

    it("lets a real href navigate so target='_blank' can open a new tab", async () => {
        const { wrapper, defaultPrevented } = await clickAndCheckDefaultPrevented(stories.ExternalDownload);

        expect(wrapper.get("a").attributes("target")).toBe("_blank");
        expect(defaultPrevented).toBe(false);
        expect(wrapper.emitted("click")).toHaveLength(1);
    });

    it("cancels navigation and emits nothing when disabled", async () => {
        const { wrapper, defaultPrevented } = await clickAndCheckDefaultPrevented(stories.DisabledDownload);

        expect(defaultPrevented).toBe(true);
        expect(wrapper.emitted("click")).toBeUndefined();
    });
});
