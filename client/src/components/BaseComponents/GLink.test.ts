import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import * as GLinkStories from "./GLink.stories";
import { createMemoryRouter } from "./test-utils";

import GLink from "./GLink.vue";

const stories = composeStories(GLinkStories);
const mountStory = useStoryMount();

const ROW_CLICKS = '[data-description="row clicks"]';

/** The link's own `click` emissions; the story mount's root is the story, not the link. */
function clicks(wrapper: VueWrapper) {
    return wrapper.getComponent(GLink).emitted("click");
}

describe("GLink.vue link targets", () => {
    // Galaxy can be served under a URL prefix, so a router link's href has to come from
    // the router, which knows the base -- open-in-new-tab and copy-link use it as is.
    it("renders a router link's href with the router base", () => {
        const wrapper = mountStory(stories.InternalLink, { router: createMemoryRouter({ base: "/galaxypf/" }) });

        expect(wrapper.get("a").attributes("href")).toBe("/galaxypf/pages/create");
    });

    it("renders a plain anchor's href as given", () => {
        const wrapper = mountStory(stories.ExternalLink);

        expect(wrapper.get("a").attributes("href")).toBe("https://example.org/data.txt");
    });

    it("renders no href when disabled", () => {
        const wrapper = mountStory(stories.Disabled);

        expect(wrapper.get("button").attributes("href")).toBeUndefined();
    });

    // Vue 3 renders `aria-disabled="false"` for a bound false, which breaks `:not([aria-disabled])` selectors.
    it("leaves aria-disabled off an enabled anchor", () => {
        const wrapper = mountStory(stories.ExternalLink);

        expect(wrapper.get("a").attributes("aria-disabled")).toBeUndefined();
    });

    it("leaves aria-disabled off an enabled router link", () => {
        const wrapper = mountStory(stories.InternalLink, { router: createMemoryRouter() });

        expect(wrapper.get("a").attributes("aria-disabled")).toBeUndefined();
    });

    it("sets aria-disabled to true on a disabled link", () => {
        const wrapper = mountStory(stories.Disabled);

        expect(wrapper.get("button").attributes("aria-disabled")).toBe("true");
    });

    // A styled tooltip replaces the native title. RouterLink runs in Vue 3 mode, where a
    // `false` attribute renders as the string "false" instead of being dropped.
    it("leaves the native title off a router link with a tooltip", () => {
        const wrapper = mountStory(stories.InternalLink, { router: createMemoryRouter() });

        expect(wrapper.get("a").attributes("title")).toBeUndefined();
    });
});

describe("GLink.vue clicks", () => {
    // The click listener reaches the RouterLink's rendered anchor by fallthrough, alongside
    // RouterLink's own navigation handler.
    it("emits click exactly once from a router link", async () => {
        const wrapper = mountStory(stories.InternalLink, { router: createMemoryRouter() });

        await wrapper.get("a").trigger("click");

        expect(clicks(wrapper)).toHaveLength(1);
    });

    it("emits click exactly once from a plain anchor", async () => {
        const wrapper = mountStory(stories.ExternalLink);

        await wrapper.get("a").trigger("click");

        expect(clicks(wrapper)).toHaveLength(1);
    });

    // A disabled link renders `aria-disabled`, not a native disabled control, so its click
    // guard has to stop the event before it reaches clickable ancestors.
    it("emits no click and stops the event when disabled", async () => {
        const wrapper = mountStory(stories.InClickableRow, { props: { disabled: true } });

        await wrapper.get("button").trigger("click");

        expect(clicks(wrapper)).toBeUndefined();
        expect(wrapper.get(ROW_CLICKS).text()).toBe("Row clicks: 0");
    });

    it("lets an enabled link's click reach clickable ancestors", async () => {
        const wrapper = mountStory(stories.InClickableRow);

        await wrapper.get("a").trigger("click");

        expect(clicks(wrapper)).toHaveLength(1);
        expect(wrapper.get(ROW_CLICKS).text()).toBe("Row clicks: 1");
    });
});
