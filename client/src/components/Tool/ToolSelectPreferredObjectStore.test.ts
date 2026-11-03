import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { ROOT_COMPONENT } from "@/utils/navigation/schema";

import * as ToolSelectPreferredObjectStoreStories from "./ToolSelectPreferredObjectStore.stories";

import ToolSelectPreferredObjectStore from "./ToolSelectPreferredObjectStore.vue";

const stories = composeStories(ToolSelectPreferredObjectStoreStories);
const mountStory = useStoryMount();

const SELECTION = ROOT_COMPONENT.preferences.object_store_selection;
const SELECTION_ERROR = ".object-store-selection-error";

/** Mounts a story and waits for the storage locations to load. */
async function mountSelector(story: StoryOf<typeof stories>) {
    const wrapper = mountStory(story);
    await flushPromises();
    return wrapper.findComponent(ToolSelectPreferredObjectStore);
}

// The listed options are covered by the OffersEachStorageLocation play function.
describe("ToolSelectPreferredObjectStore.vue", () => {
    it.each([
        { story: "UsesDefaults", selected: "object_store_1", emitted: "object_store_1" },
        { story: "PreferredStorage", selected: "__null__", emitted: null },
    ] as const)("emits $emitted when $selected is selected in $story", async ({ story, selected, emitted }) => {
        const selector = await mountSelector(stories[story]);
        const selectButton = selector.find(SELECTION.option_card_select({ object_store_id: selected }).selector);
        expect(selectButton.exists()).toBe(true);

        await selectButton.trigger("click");
        await flushPromises();

        expect(selector.find(SELECTION_ERROR).exists()).toBe(false);
        expect(selector.emitted("updated")).toEqual([[emitted]]);
    });
});
