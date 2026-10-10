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

function drawnAt(size: string) {
    return expect.arrayContaining([`fa-${size}`]);
}

describe("ObjectStoreBadges", () => {
    it("renders every badge at the default lg size when no size is given", () => {
        const wrapper = mountStory(stories.DefaultSize);

        expect(wrapper.find(BADGE_LIST).exists()).toBe(true);
        expect(renderedBadges(wrapper)).toEqual([
            { badge: badges[0], size: "lg", iconClasses: drawnAt("lg") },
            { badge: badges[1], size: "lg", iconClasses: drawnAt("lg") },
        ]);
    });

    it("passes an explicit size to every badge", () => {
        const wrapper = mountStory(stories.DoubleSize);

        expect(wrapper.find(BADGE_LIST).exists()).toBe(true);
        expect(renderedBadges(wrapper)).toEqual([
            { badge: badges[0], size: "2x", iconClasses: drawnAt("2x") },
            { badge: badges[1], size: "2x", iconClasses: drawnAt("2x") },
        ]);
    });

    it("should pass along whether badges are interactive", async () => {
        const wrapper = mountStory(stories.NonInteractive);
        const badges = wrapper.findAllComponents(ObjectStoreBadge);
        expect(badges.at(0)!.props("interactive")).toBe(false);
        expect(badges.at(1)!.props("interactive")).toBe(false);
    });
});
