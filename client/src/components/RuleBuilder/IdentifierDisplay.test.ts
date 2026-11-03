import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it, vi } from "vitest";

import * as IdentifierDisplayStories from "./IdentifierDisplay.stories";

const stories = composeStories(IdentifierDisplayStories);
const mountStory = useStoryMount();

describe("IdentifierDisplay", () => {
    // The rule builder highlights a mapping's columns while the pointer is over it.
    it("passes mouseover and mouseout on to the parent", async () => {
        const { onMouseover, onMouseout } = IdentifierDisplayStories.default.args;
        vi.mocked(onMouseover).mockClear();
        vi.mocked(onMouseout).mockClear();
        const wrapper = mountStory(stories.SampleIdentifiers);

        await wrapper.get("li").trigger("mouseover");
        await wrapper.get("li").trigger("mouseout");

        expect(onMouseover).toHaveBeenCalledTimes(1);
        expect(onMouseout).toHaveBeenCalledTimes(1);
    });
});
