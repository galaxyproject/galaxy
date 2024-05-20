import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import VaultSecret from "./VaultSecret.vue";

const localVue = getLocalVue(true);

describe("VaultSecret", () => {
    it("should render a form element", async () => {
        const wrapper = shallowMount(VaultSecret, {
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
});
