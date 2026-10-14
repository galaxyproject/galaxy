import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import * as DelayedInputStories from "./DelayedInput.stories";

const stories = composeStories(DelayedInputStories);
const mountStory = useStoryMount();

describe("DelayedInput.vue", () => {
    it("clears search text when the clear button is clicked", async () => {
        const wrapper = mountStory(stories.WithQuery);
        expect(wrapper.get<HTMLInputElement>("input.g-form-input").element.value).toBe("fastp");

        await wrapper.get("button.search-clear").trigger("click");
        await nextTick();

        expect(wrapper.find("input.g-form-input").exists()).toBe(true);
        expect(wrapper.get<HTMLInputElement>("input.g-form-input").element.value).toBe("");
    });
});
