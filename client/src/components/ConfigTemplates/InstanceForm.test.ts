import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import type { FormEntry } from "./formUtil";

import InstanceForm from "./InstanceForm.vue";

const globalConfig = getLocalVue();

const inputs: FormEntry[] = [];
const SUBMIT_TITLE = "Submit the form!";

describe("InstanceForm", () => {
    it("should render a loading message and not submit button if inputs is null", async () => {
        const wrapper = shallowMount(InstanceForm as object, {
            props: {
                title: "MY FORM",
                inputs: null,
                submitTitle: SUBMIT_TITLE,
                busy: false,
                loadingMessage: "loading plugin instance",
            },
            global: globalConfig.global,
        });
        const loadingSpan = wrapper.findComponent({ name: "LoadingSpan" }).exists();
        expect(loadingSpan).toBeTruthy();
        expect(wrapper.find("#submit").exists()).toBeFalsy();
    });

    it("should hide a loading message after loading", async () => {
        const wrapper = shallowMount(InstanceForm as object, {
            props: {
                title: "MY FORM",
                inputs: inputs,
                submitTitle: SUBMIT_TITLE,
                busy: false,
                loadingMessage: "loading plugin instance",
            },
            global: globalConfig.global,
        });
        const loadingSpan = wrapper.findComponent({ name: "LoadingSpan" }).exists();
        expect(loadingSpan).toBeFalsy();
        expect(wrapper.find("#submit").exists()).toBeTruthy();
        // Check if button contains the text (might be wrapped in additional elements)
        expect(wrapper.find("#submit").text()).toContain(SUBMIT_TITLE);
    });
});
