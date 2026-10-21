import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MAX_DESCRIPTION_LENGTH } from "@/components/Libraries/library-utils";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import LibraryEditField from "./LibraryEditField.vue";

const localVue = getLocalVue();
const sanitizeSpy = vi.mocked(sanitizeHtml);
const originalSanitizeImplementation = sanitizeSpy.getMockImplementation();

enableAutoUnmount(afterEach);

function mountLibraryEditField(props) {
    return shallowMount(LibraryEditField, { global: localVue, props });
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
        const text = "See https://usegalaxy.org <em>now</em>";
        const linkifiedHtml =
            '<span class="sanitized">See <a href="https://usegalaxy.org">https://usegalaxy.org</a> <em>now</em></span>';
        const wrapper = mountLibraryEditField({ text });

        expect(sanitizeSpy.mock.calls).toEqual([[text], [linkifiedHtml, "default"]]);
        expect(wrapper.get(".sanitized a").attributes("href")).toBe("https://usegalaxy.org");
        expect(wrapper.get(".sanitized em").text()).toBe("now");
    });

    it("sanitizes the shortened text when the description is collapsed", () => {
        const shortenedText = "x".repeat(MAX_DESCRIPTION_LENGTH);
        const text = `${shortenedText}-tail-text`;
        const wrapper = mountLibraryEditField({ text });

        expect(sanitizeSpy.mock.calls).toEqual([
            [shortenedText],
            [`<span class="sanitized">${shortenedText}</span>`, "default"],
        ]);
        expect(wrapper.get(".shrinked-description .sanitized").text()).toBe(shortenedText);
        expect(wrapper.get(".shrinked-description").attributes("title")).toBe(text);
    });

    it("renders the complete description when expanded", () => {
        const text = `${"x".repeat(MAX_DESCRIPTION_LENGTH)}-tail-text`;
        const wrapper = mountLibraryEditField({ text, isExpanded: true });

        expect(sanitizeSpy.mock.calls).toEqual([[text], [`<span class="sanitized">${text}</span>`, "default"]]);
        expect(wrapper.get(".sanitized").text()).toBe(text);
        expect(wrapper.find(".shrinked-description").exists()).toBe(false);
    });

    it.each([
        { state: "collapsed", isExpanded: false, label: "(more)" },
        { state: "expanded", isExpanded: true, label: "(less)" },
    ])("emits an expansion toggle when $label is clicked in the $state description", async ({ isExpanded, label }) => {
        const wrapper = mountLibraryEditField({ text: "x".repeat(MAX_DESCRIPTION_LENGTH + 10), isExpanded });
        const toggleLink = wrapper.get(".more-text-btn");
        expect(toggleLink.text()).toBe(label);

        await toggleLink.trigger("click");

        expect(wrapper.emitted("toggleDescriptionExpand")).toEqual([[]]);
    });
});
