import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as WorkflowHelpDisplayStories from "./WorkflowHelpDisplay.stories";

const stories = composeStories(WorkflowHelpDisplayStories);

const sanitizeSpy = vi.mocked(sanitizeHtml);
const originalSanitizeImplementation = sanitizeSpy.getMockImplementation();

beforeEach(() => {
    sanitizeSpy.mockClear();
    sanitizeSpy.mockImplementation((html) => `<span class="sanitized">${html}</span>`);
});

afterEach(() => {
    sanitizeSpy.mockReset();
    if (originalSanitizeImplementation) {
        sanitizeSpy.mockImplementation(originalSanitizeImplementation);
    }
});
// afterEach runs in reverse order: unmount before restoring the sanitizer.
const mountStory = useStoryMount();

describe("WorkflowHelpDisplay", () => {
    it("renders readme and help markdown through v-sanitize-html with the links profile", () => {
        const wrapper = mountStory(stories.ReadmeAndHelp);

        const calls = vi.mocked(sanitizeHtml).mock.calls;
        expect(calls).toHaveLength(2);
        const [readmeHtml, readmeProfile] = nth(calls, 0);
        expect(readmeProfile).toBe("links");
        expect(readmeHtml).toContain("<strong>Readme</strong>");
        expect(readmeHtml).toContain('target="_blank"');
        expect(readmeHtml).toContain("&lt;em&gt;raw&lt;/em&gt;");
        expect(nth(calls, 1)[1]).toBe("links");

        const rendered = wrapper.findAll(".container .sanitized");
        expect(rendered).toHaveLength(2);
        expect(nth(rendered, 1).html()).toContain("<em>text</em>");
    });
});
