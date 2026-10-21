import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it, vi } from "vitest";

import * as componentStories from "./Index.stories";

import Index from "./Index.vue";

const stories = composeStories(componentStories);
const mountStory = useStoryMount();

describe("HistoryExport", () => {
    it("shows export tabs when writable file sources are available", async () => {
        const wrapper = mountStory(stories.WritableRepository).getComponent(Index);
        await vi.waitFor(() => expect(wrapper.findComponent(".history-export-tabs").exists()).toBe(true));

        const tabs = wrapper.findComponent(".history-export-tabs");
        expect(tabs.exists()).toBeTruthy();
    });
});
