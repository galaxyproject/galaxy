import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import { type FormEntry } from "./formUtil";

import InstanceForm from "./InstanceForm.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const localVue = getLocalVue(true);

const inputs: FormEntry[] = [];
const SUBMIT_TITLE = "Submit the form!";

describe("InstanceForm", () => {
    it("should render a loading message and not submit button if inputs is null", async () => {
        const wrapper = shallowMount(InstanceForm as any, {
            propsData: {
                title: "MY FORM",
                inputs: null,
                submitTitle: SUBMIT_TITLE,
                busy: false,
                loadingMessage: "loading plugin instance",
            },
            localVue,
        });
        const loadingSpan = wrapper.findComponent(LoadingSpan).exists();
        expect(loadingSpan).toBeTruthy();
        expect(wrapper.find("#submit").exists()).toBeFalsy();
    });

    it("should hide a loading message after loading", async () => {
        const wrapper = shallowMount(InstanceForm as any, {
            propsData: {
                title: "MY FORM",
                inputs: inputs,
                submitTitle: SUBMIT_TITLE,
                busy: false,
                loadingMessage: "loading plugin instance",
            },
            localVue,
        });
        const loadingSpan = wrapper.findComponent(LoadingSpan).exists();
        expect(loadingSpan).toBeFalsy();
        expect(wrapper.find("#submit").exists()).toBeTruthy();
        expect(wrapper.find("#submit").text()).toEqual(SUBMIT_TITLE);
    });
});
