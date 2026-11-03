import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import * as ShowSelectedObjectStoreStories from "./ShowSelectedObjectStore.stories";

import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";

const stories = composeStories(ShowSelectedObjectStoreStories);
const mountStory = useStoryMount();

describe("ShowSelectedObjectStore", () => {
    it("shows loading before describing the selected Galaxy object store", async () => {
        const wrapper = mountStory(stories.GalaxyStorage, { instrumentLocalization: true });
        const loadingEl = wrapper.findComponent(LoadingSpan);
        expect(loadingEl.exists()).toBeTruthy();
        expect(loadingEl.get(".loading-message").text()).toContain("Loading Galaxy storage details");
        await flushPromises();
        expect(wrapper.findComponent(LoadingSpan).exists()).toBeFalsy();
        expect(wrapper.findComponent(DescribeObjectStore).exists()).toBeTruthy();
        // Shown inside hover popovers, which can't hold another interactive popover.
        expect(wrapper.findComponent(DescribeObjectStore).props("interactive")).toBe(false);
        expect(wrapper.getComponent(DescribeObjectStore).props("storageInfo").object_store_id).toBe(
            stories.GalaxyStorage.args.preferredObjectStoreId,
        );
    });

    it("loads URI IDs through the user object-store instance API", async () => {
        const wrapper = mountStory(stories.UserStorage, { instrumentLocalization: true });
        const loadingEl = wrapper.findComponent(LoadingSpan);
        expect(loadingEl.exists()).toBeTruthy();
        expect(loadingEl.get(".loading-message").text()).toContain("Loading Galaxy storage details");
        await flushPromises();
        expect(wrapper.findComponent(LoadingSpan).exists()).toBeFalsy();
        expect(wrapper.findComponent(DescribeObjectStore).exists()).toBeTruthy();
        expect(wrapper.getComponent(DescribeObjectStore).props("storageInfo").object_store_id).toBe(
            stories.UserStorage.args.preferredObjectStoreId,
        );
    });
});
