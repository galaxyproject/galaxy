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

    it.each([
        { story: stories.AdminConfigured, author: "an admin" },
        { story: stories.UserDefined, author: "a user" },
    ])("converts configuration markup by $author from markdown to HTML", ({ story }) => {
        const wrapper = mountStory(story);

        expect(wrapper.html()).toContain("<em>not backed up</em>");
    });

    it("allows HTML in configuration markup explicitly set by the admin", () => {
        const wrapper = mountStory(stories.AdminConfigured);

        expect(wrapper.html()).toContain("<b>Purged after 30 days.</b>");
    });

    it("escapes HTML in configuration markup not sourced from the admin", () => {
        const wrapper = mountStory(stories.UserDefined);

        expect(wrapper.html()).not.toContain("<b>Purged after 30 days.</b>");
        expect(wrapper.text()).toBe(
            'Scratch space, not backed up. <b>Purged after 30 days.</b> See the <a href="https://example.org" target="_blank">storage policy</a>.',
        );
    });

    it("renders through v-sanitize-html with the links profile", () => {
        mountStory(stories.AdminConfigured);

        expect(sanitizeHtml).toHaveBeenCalledWith(
            '<p>Scratch space, <em>not backed up</em>. <b>Purged after 30 days.</b> See the <a href="https://example.org" target="_blank">storage policy</a>.</p>\n',
            "links",
        );
    });
});
