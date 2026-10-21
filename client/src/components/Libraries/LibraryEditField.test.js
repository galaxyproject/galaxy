import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MAX_DESCRIPTION_LENGTH } from "@/components/Libraries/library-utils";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as LibraryEditFieldStories from "./LibraryEditField.stories";

import LibraryEditField from "./LibraryEditField.vue";

const stories = composeStories(LibraryEditFieldStories);
const mountStory = useStoryMount();
const sanitizeSpy = vi.mocked(sanitizeHtml);
const originalSanitizeImplementation = sanitizeSpy.getMockImplementation();

function mountLibraryEditField(story) {
    return mountStory(story).getComponent(LibraryEditField);
}

describe("LibraryEditField", () => {
    beforeEach(() => {
        sanitizeSpy.mockClear();
        sanitizeSpy.mockImplementation((html) => `<span class="sanitized">${html}</span>`);
    });

    afterEach(() => {
        sanitizeSpy.mockReset();
        sanitizeSpy.mockImplementation(originalSanitizeImplementation);
    });

    it("sanitizes before linkifying, then sanitizes the rendered HTML with the default profile", () => {
        const text = stories.LinkedDescription.args.text;
        const linkifiedHtml =
            '<span class="sanitized">See <a href="https://usegalaxy.org">https://usegalaxy.org</a> <em>now</em></span>';
        const wrapper = mountLibraryEditField(stories.LinkedDescription);

        expect(sanitizeSpy.mock.calls).toEqual([[text], [linkifiedHtml, "default"]]);
        expect(wrapper.get(".sanitized a").attributes("href")).toBe("https://usegalaxy.org");
        expect(wrapper.get(".sanitized em").text()).toBe("now");
    });

    it("sanitizes the shortened text when the description is collapsed", () => {
        const text = stories.CollapsedDescription.args.text;
        const shortenedText = text.substring(0, MAX_DESCRIPTION_LENGTH);
        const wrapper = mountLibraryEditField(stories.CollapsedDescription);

        expect(sanitizeSpy.mock.calls).toEqual([
            [shortenedText],
            [`<span class="sanitized">${shortenedText}</span>`, "default"],
        ]);
        expect(wrapper.get(".shrinked-description .sanitized").text()).toBe(shortenedText);
        expect(wrapper.get(".shrinked-description").attributes("title")).toBe(text);
    });

    it("renders the complete description when expanded", () => {
        const text = stories.ExpandedDescription.args.text;
        const wrapper = mountLibraryEditField(stories.ExpandedDescription);

        expect(sanitizeSpy.mock.calls).toEqual([[text], [`<span class="sanitized">${text}</span>`, "default"]]);
        expect(wrapper.get(".sanitized").text()).toBe(text);
        expect(wrapper.find(".shrinked-description").exists()).toBe(false);
    });

    it.each([
        { state: "collapsed", story: stories.CollapsedDescription, label: "(more)" },
        { state: "expanded", story: stories.ExpandedDescription, label: "(less)" },
    ])("emits an expansion toggle when $label is clicked in the $state description", async ({ story, label }) => {
        const wrapper = mountLibraryEditField(story);
        const toggleLink = wrapper.get(".more-text-btn");
        expect(toggleLink.text()).toBe(label);

        await toggleLink.trigger("click");

        expect(wrapper.emitted("toggleDescriptionExpand")).toEqual([[]]);
    });
});
