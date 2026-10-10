import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import * as BroadcastsListStories from "./BroadcastsList.stories";

import Heading from "@/components/Common/Heading.vue";

const stories = composeStories(BroadcastsListStories);
const mountStory = useStoryMount();

const selectors = {
    emptyBroadcastsListAlert: "#empty-broadcast-list-alert",
    broadcastItem: "[data-test-id='broadcast-item']",
} as const;

const filterButtons = {
    active: "#show-active-filter-button",
    scheduled: "#show-scheduled-filter-button",
    expired: "#show-expired-filter-button",
} as const;

type Filter = keyof typeof filterButtons;

// The subjects of `OneOfEach`'s broadcasts, in alphabetical order.
// Repeated here, since a stories file exports only stories.
const ACTIVE = "Galaxy 26.1 is live";
const SCHEDULED = "Maintenance on Saturday";
const EXPIRED = "Storage outage resolved";

async function mountBroadcastsList(story: StoryOf<typeof stories>) {
    const wrapper = mountStory(story);
    await flushPromises();
    return wrapper;
}

type Wrapper = Awaited<ReturnType<typeof mountBroadcastsList>>;

async function toggleFilters(wrapper: Wrapper, ...filters: Filter[]) {
    for (const filter of filters) {
        await wrapper.find(filterButtons[filter]).trigger("click");
    }
}

/** The shown broadcasts' subjects, sorted so the list's own order doesn't matter. */
function shownSubjects(wrapper: Wrapper) {
    return wrapper
        .findAll(selectors.broadcastItem)
        .map((item) => item.findComponent(Heading).text())
        .sort();
}

describe("BroadcastsList.vue", () => {
    it("shows the empty-list alert when there are no broadcasts", async () => {
        const wrapper = await mountBroadcastsList(stories.NoBroadcasts);

        expect(wrapper.findAll(selectors.broadcastItem)).toHaveLength(0);
        expect(wrapper.find(selectors.emptyBroadcastsListAlert).exists()).toBe(true);
    });

    it("lists active, scheduled and expired broadcasts while every filter is on", async () => {
        const wrapper = await mountBroadcastsList(stories.OneOfEach);

        expect(shownSubjects(wrapper)).toEqual([ACTIVE, SCHEDULED, EXPIRED]);
        expect(wrapper.find(selectors.emptyBroadcastsListAlert).exists()).toBe(false);
    });

    it.each([
        { off: ["scheduled", "expired"], shown: ACTIVE },
        { off: ["active", "expired"], shown: SCHEDULED },
        { off: ["active", "scheduled"], shown: EXPIRED },
    ] as const)("lists only $shown with the $off filters off", async ({ off, shown }) => {
        const wrapper = await mountBroadcastsList(stories.OneOfEach);

        await toggleFilters(wrapper, ...off);

        expect(shownSubjects(wrapper)).toEqual([shown]);
    });

    it("shows the empty-list alert with every filter off, and lists broadcasts again as filters are switched back on", async () => {
        const wrapper = await mountBroadcastsList(stories.OneOfEach);

        await toggleFilters(wrapper, "active", "scheduled", "expired");
        expect(shownSubjects(wrapper)).toEqual([]);
        expect(wrapper.find(selectors.emptyBroadcastsListAlert).exists()).toBe(true);

        await toggleFilters(wrapper, "active");
        expect(shownSubjects(wrapper)).toEqual([ACTIVE]);

        await toggleFilters(wrapper, "scheduled");
        expect(shownSubjects(wrapper)).toEqual([ACTIVE, SCHEDULED]);

        await toggleFilters(wrapper, "expired");
        expect(shownSubjects(wrapper)).toEqual([ACTIVE, SCHEDULED, EXPIRED]);
    });
});
