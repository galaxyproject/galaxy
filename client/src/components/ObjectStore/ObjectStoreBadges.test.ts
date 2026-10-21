import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import * as ObjectStoreBadgesStories from "./ObjectStoreBadges.stories";

import ObjectStoreBadge from "./ObjectStoreBadge.vue";

const stories = composeStories(ObjectStoreBadgesStories);
const mountStory = useStoryMount();

const BADGE_LIST = ".object-store-badges";

const badges = stories.DefaultSize.args.badges!;

/** Each badge's data and size as passed down, plus the icon layer's classes. */
function renderedBadges(wrapper: VueWrapper) {
    return wrapper.findAllComponents(ObjectStoreBadge).map((badge) => ({
        badge: badge.props("badge"),
        size: badge.props("size"),
        iconClasses: badge.get("[data-badge-type]").classes(),
    }));
}

// What each badge shows and its tooltip are covered by the play functions.
describe("ObjectStoreBadges", () => {
    it.each([
        ["DefaultSize", "lg"],
        ["DoubleSize", "2x"],
    ] as const)("passes each badge's full data down in %s, drawn at %s", (story, size) => {
        const wrapper = mountStory(stories[story]);

        expect(wrapper.find(BADGE_LIST).exists()).toBe(true);
        const drawn = { size, iconClasses: expect.arrayContaining([`fa-${size}`]) };
        expect(renderedBadges(wrapper)).toEqual(badges.map((badge) => ({ badge, ...drawn })));
    });

    it("should pass along whether badges are interactive", async () => {
        const wrapper = mountStory(stories.NonInteractive);
        const badges = wrapper.findAllComponents(ObjectStoreBadge);
        expect(badges.at(0)!.props("interactive")).toBe(false);
        expect(badges.at(1)!.props("interactive")).toBe(false);
    });
});
