import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

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
});
