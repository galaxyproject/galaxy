import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import ConfigurationMarkdown from "./ConfigurationMarkdown.vue";

const localVue = getLocalVue();

function mountConfigurationMarkdown(markdown: string, admin: boolean) {
    return shallowMount(ConfigurationMarkdown, { props: { markdown, admin }, global: localVue });
}

describe("ConfigurationMarkdown.vue", () => {
    beforeEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });

    it("converts the supplied configuration markup from markdown to HTML", () => {
        const wrapper = mountConfigurationMarkdown("the *content*", true);

        expect(wrapper.html()).toContain("<em>content</em>");
    });

    it("allows HTML in configuration markup explicitly set by the admin", () => {
        const wrapper = mountConfigurationMarkdown("the <b>content</b>", true);

        expect(wrapper.html()).toContain("<b>content</b>");
    });

    it("escapes HTML in configuration markup not sourced from the admin", () => {
        const wrapper = mountConfigurationMarkdown("the <b>content</b>", false);

        expect(wrapper.html()).not.toContain("<b>content</b>");
        expect(wrapper.text()).toBe("the <b>content</b>");
    });

    it("renders through v-sanitize-html with the links profile", () => {
        mountConfigurationMarkdown('the <a href="https://example.org" target="_blank">link</a>', true);

        expect(sanitizeHtml).toHaveBeenCalledWith(
            '<p>the <a href="https://example.org" target="_blank">link</a></p>\n',
            "links",
        );
    });
});
