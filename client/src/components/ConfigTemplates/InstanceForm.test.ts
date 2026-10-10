import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { FormEntry } from "./formUtil";

import InstanceForm from "./InstanceForm.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const SUBMIT_TITLE = "Submit the form!";
const LOADING_MESSAGE = "loading plugin instance";
const SUBMIT_BUTTON = "#submit";

enableAutoUnmount(afterEach);

function mountInstanceForm(inputs: FormEntry[] | null | undefined) {
    return shallowMount(InstanceForm, {
        props: {
            title: "MY FORM",
            // null is outside the prop type, but the template's loose `== undefined` treats it as loading too.
            inputs: inputs as FormEntry[] | undefined,
            submitTitle: SUBMIT_TITLE,
            busy: false,
            loadingMessage: LOADING_MESSAGE,
        },
        global: getLocalVue(true),
    });
}

describe("InstanceForm", () => {
    it.each([undefined, null])("shows the loading message and no submit button while inputs are %s", (inputs) => {
        const wrapper = mountInstanceForm(inputs);

        const loading = wrapper.findComponent(LoadingSpan);
        expect(loading.exists()).toBe(true);
        expect(loading.props("message")).toBe(LOADING_MESSAGE);
        expect(wrapper.find(SUBMIT_BUTTON).exists()).toBe(false);
    });

    it("replaces the loading message with a titled submit button once inputs load", () => {
        const wrapper = mountInstanceForm([]);

        expect(wrapper.findComponent(LoadingSpan).exists()).toBe(false);
        const submit = wrapper.find(SUBMIT_BUTTON);
        expect(submit.exists()).toBe(true);
        expect(submit.text()).toBe(SUBMIT_TITLE);
    });
});
