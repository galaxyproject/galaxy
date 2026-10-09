import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { BFormTextarea } from "bootstrap-vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import VaultSecret from "./VaultSecret.vue";

enableAutoUnmount(afterEach);

describe("VaultSecret", () => {
    beforeEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });

    it("renders the secret label and Markdown help", () => {
        const wrapper = shallowMount(VaultSecret, {
            props: {
                name: "secret name",
                label: "Label Secret",
                help: "here is some good *help*",
                isSet: true,
            },
            global: getLocalVue(true),
        });
        const titleWrapper = wrapper.find(".ui-form-title-text");
        expect(titleWrapper.text()).toEqual("Label Secret");
        const helpWrapper = wrapper.find(".ui-form-info p");
        expect(helpWrapper.html()).toEqual("<p>here is some good <em>help</em></p>");
    });

    it("renders a textarea editor for multiline secrets", () => {
        const wrapper = shallowMount(VaultSecret, {
            props: {
                name: "secret name",
                label: "Label Secret",
                help: "pem help",
                isSet: true,
                multiline: true,
            },
            global: getLocalVue(true),
        });
        expect(wrapper.findComponent(BFormTextarea).exists()).toBe(true);
    });

    it("sanitizes Markdown help with the links profile", () => {
        shallowMount(VaultSecret, {
            props: { name: "secret", label: "Secret", help: "the *help*", isSet: false },
            global: getLocalVue(true),
        });
        expect(sanitizeHtml).toHaveBeenCalledWith("<p>the <em>help</em></p>\n", "links");
    });
});
