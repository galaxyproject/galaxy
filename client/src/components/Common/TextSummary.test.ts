import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as TextSummaryStories from "./TextSummary.stories";

const stories = composeStories(TextSummaryStories);
const mountStory = useStoryMount();

const DESCRIPTION = stories.PlainText.args.description;

describe("TextSummary", () => {
    it("renders the description as text by default", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const paragraph = mountStory(stories.PlainText).get(".html-paragraph");

        expect(paragraph.find("b").exists()).toBe(false);
        expect(paragraph.text()).toBe(DESCRIPTION);
        expect(sanitizeHtml).not.toHaveBeenCalled();
    });

    it("renders the description through v-sanitize-html when isHtml is set", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const paragraph = mountStory(stories.RenderedHtml).get(".html-paragraph");

        expect(sanitizeHtml).toHaveBeenCalledWith(DESCRIPTION, "default");
        expect(paragraph.get("b").text()).toBe("paired");
    });
});
