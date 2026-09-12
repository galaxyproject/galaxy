import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormSection from "./FormSection.vue";
import FormElement from "@/components/Form/FormElement.vue";

const localVue = getLocalVue();

function mountFormSection(supportsJobBasedActions?: boolean) {
    return shallowMount(FormSection as any, {
        localVue,
        propsData: {
            id: 0,
            nodeInputs: [],
            nodeOutputs: [{ name: "output" }],
            step: { id: 0, type: "pick_value" },
            datatypes: [],
            postJobActions: {},
            supportsJobBasedActions,
        },
    });
}

describe("FormSection", () => {
    it("shows job-based actions by default", () => {
        const wrapper = mountFormSection();

        expect(wrapper.findAllComponents(FormElement)).toHaveLength(2);
    });

    it("hides job-based actions when the step cannot execute them", () => {
        const wrapper = mountFormSection(false);

        expect(wrapper.findAllComponents(FormElement)).toHaveLength(0);
    });
});
