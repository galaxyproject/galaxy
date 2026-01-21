import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import VaultSecret from "./VaultSecret.vue";

const localVue = getLocalVue(true);

describe("VaultSecret", () => {
    it("should render a form element", async () => {
        const wrapper = shallowMount(VaultSecret as object, {
            props: {
                name: "secret name",
                label: "Label Secret",
                help: "here is some good *help*",
                isSet: true,
            },
            global: localVue,
        });
        const titleWrapper = wrapper.find(".ui-form-title-text");
        expect(titleWrapper.text()).toEqual("Label Secret");
        const helpWrapper = wrapper.find(".ui-form-info p");
        // verify markdown converted
        expect(helpWrapper.html()).toEqual("<p>here is some good <em>help</em></p>");
    });
});
