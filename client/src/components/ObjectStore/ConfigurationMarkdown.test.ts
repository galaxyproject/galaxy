import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as ConfigurationMarkdownStories from "./ConfigurationMarkdown.stories";

const stories = composeStories(ConfigurationMarkdownStories);
const mountStory = useStoryMount();

describe("ConfigurationMarkdown.vue", () => {
    beforeEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });

    it("renders through v-sanitize-html with the links profile", () => {
        mountStory(stories.AdminConfigured);

        expect(sanitizeHtml).toHaveBeenCalledWith(
            '<p>Scratch space, <em>not backed up</em>. <b>Purged after 30 days.</b> See the <a href="https://example.org" target="_blank">storage policy</a>.</p>\n',
            "links",
        );
    });
});
