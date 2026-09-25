import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import VaultSecret from "./VaultSecret.vue";

const localVue = getLocalVue(true);

describe("VaultSecret", () => {
    it("should render a form element", async () => {
        const wrapper = shallowMount(VaultSecret as object, {
            propsData: {
                name: "secret name",
                label: "Label Secret",
                help: "here is some good *help*",
                isSet: true,
            },
            localVue,
        });
        const titleWrapper = wrapper.find(".ui-form-title-text");
        expect(titleWrapper.text()).toEqual("Label Secret");
        const helpWrapper = wrapper.find(".ui-form-info p");
        // verify markdown converted
        expect(helpWrapper.html()).toEqual("<p>here is some good <em>help</em></p>");
    });

    it("should render a textarea editor for multiline secrets", async () => {
        const wrapper = shallowMount(VaultSecret as object, {
            propsData: {
                name: "secret name",
                label: "Label Secret",
                help: "pem help",
                isSet: true,
                multiline: true,
            },
            localVue,
        });
        expect(wrapper.html()).toContain("bformtextarea-stub");
    });

    it("renders help through v-sanitize-html with the links profile", () => {
        vi.mocked(sanitizeHtml).mockClear();
        shallowMount(VaultSecret as object, {
            propsData: { name: "secret", label: "Secret", help: "the *help*", isSet: false },
            localVue,
        });
        expect(sanitizeHtml).toHaveBeenCalledWith("<p>the <em>help</em></p>\n", "links");
    });
});
