import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import ConfigurationMarkdown from "./ConfigurationMarkdown.vue";

const localVue = getLocalVue();

describe("ConfigurationMarkdown.vue", () => {
    let wrapper;

    it("should convert supplied configuration markup to markdown and display", () => {
        wrapper = shallowMount(ConfigurationMarkdown as object, {
            propsData: { markdown: "the *content*", admin: true },
            localVue,
        });
        expect(wrapper.html()).toContain("<em>content</em>");
    });

    it("should allow HTML in configuration markup explicitly set by the admin", () => {
        wrapper = shallowMount(ConfigurationMarkdown as object, {
            propsData: { markdown: "the <b>content</b>", admin: true },
            localVue,
        });
        expect(wrapper.html()).toContain("<b>content</b>");
    });

    it("should escape supplied HTML for non-admin sourced content", () => {
        wrapper = shallowMount(ConfigurationMarkdown as object, {
            propsData: { markdown: "the <b>content</b>", admin: false },
            localVue,
        });
        expect(wrapper.html()).not.toContain("<b>content</b>");
    });

    it("renders through v-sanitize-html with the links profile", () => {
        vi.mocked(sanitizeHtml).mockClear();
        shallowMount(ConfigurationMarkdown as object, {
            propsData: { markdown: 'the <a href="https://example.org" target="_blank">link</a>', admin: true },
            localVue,
        });
        expect(sanitizeHtml).toHaveBeenCalledWith(
            '<p>the <a href="https://example.org" target="_blank">link</a></p>\n',
            "links",
        );
    });
});
