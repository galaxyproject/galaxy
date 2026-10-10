import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as ObjectStoreRestrictionSpanStories from "./ObjectStoreRestrictionSpan.stories";

const stories = composeStories(ObjectStoreRestrictionSpanStories);
const mountStory = useStoryMount();

describe("ObjectStoreRestrictionSpan", () => {
    it.each([
        { story: "Private", text: "private", explanation: "restricted to a single user" },
        { story: "Sharable", text: "sharable", explanation: "allows standard Galaxy sharing features" },
    ])("labels $story storage and explains it on hover", ({ story, text, explanation }) => {
        const wrapper = mountStory(stories[story]);

        const span = wrapper.get(".stored-how");
        expect(span.text()).toBe(text);
        expect(span.attributes("title")).toContain(explanation);
    });
});
