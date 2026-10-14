import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MAX_DESCRIPTION_LENGTH } from "@/components/Libraries/library-utils";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import LibraryEditField from "./LibraryEditField.vue";

const localVue = getLocalVue();

function mountWith(propsData) {
    return mount(LibraryEditField, { localVue, propsData });
}

describe("LibraryEditField", () => {
    beforeEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
    });

    it("linkifies the text and renders the result through v-sanitize-html", () => {
        const text = "See https://usegalaxy.org <em>now</em>";
        const wrapper = mountWith({ text });

        const calls = vi.mocked(sanitizeHtml).mock.calls;
        // the raw text is cleaned before linkify-html sees it, and the linkified result again when rendered
        expect(calls[0][0]).toBe(text);
        const [html, profile] = calls[1];
        expect(profile).toBe("default");
        expect(html).toContain('<a href="https://usegalaxy.org">https://usegalaxy.org</a>');
        expect(html).toContain("<em>now</em>");
        expect(wrapper.find(".sanitized a").attributes("href")).toBe("https://usegalaxy.org");
    });

    it("sanitizes the shortened text when the description is collapsed", () => {
        const text = "x".repeat(MAX_DESCRIPTION_LENGTH + 10);
        const wrapper = mountWith({ text });

        expect(sanitizeHtml).toHaveBeenCalledWith("x".repeat(MAX_DESCRIPTION_LENGTH));
        expect(wrapper.find(".shrinked-description .sanitized").exists()).toBe(true);
    });
});
