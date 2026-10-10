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

// The stories' plays check hrefs, aria-disabled, titles and the other clicks. These need a
// router with a base, or click a plain anchor, which would navigate Storybook away.
describe("GLink.vue link targets", () => {
    // Galaxy can be served under a URL prefix, so a router link's href has to come from
    // the router, which knows the base -- open-in-new-tab and copy-link use it as is.
    it("renders a router link's href with the router base", () => {
        const wrapper = mountStory(stories.InternalLink, { router: createMemoryRouter({ base: "/galaxypf/" }) });

        expect(wrapper.get("a").attributes("href")).toBe("/galaxypf/pages/create");
    });
});

describe("GLink.vue clicks", () => {
    it("emits click exactly once from a plain anchor", async () => {
        const wrapper = mountStory(stories.ExternalLink);

        await wrapper.get("a").trigger("click");

        expect(clicks(wrapper)).toHaveLength(1);
    });

    it("lets an enabled link's click reach clickable ancestors", async () => {
        const wrapper = mountStory(stories.InClickableRow);

        await wrapper.get("a").trigger("click");

        expect(clicks(wrapper)).toHaveLength(1);
        expect(wrapper.get(ROW_CLICKS).text()).toBe("Row clicks: 1");
    });
});
