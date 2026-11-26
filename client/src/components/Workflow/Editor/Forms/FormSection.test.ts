import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormSection from "./FormSection.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import FormElement from "@/components/Form/FormElement.vue";

const localVue = getLocalVue();

function mountFormSection(supportsJobBasedActions?: boolean, postJobActions: object = {}) {
    return shallowMount(FormSection as any, {
        localVue,
        propsData: {
            id: 0,
            nodeInputs: [],
            nodeOutputs: [{ name: "output" }],
            step: { id: 0, type: "pick_value" },
            datatypes: [],
            postJobActions,
            supportsJobBasedActions,
        },
    });
}

describe("FormSection", () => {
    it("does not offer new email actions", () => {
        const wrapper = mountFormSection();

        expect(wrapper.findAllComponents(FormElement)).toHaveLength(1);
    });

    it("explains that existing email actions are inactive and allows removing them", async () => {
        const wrapper = mountFormSection(true, {
            EmailActionoutput: {
                action_type: "EmailAction",
                output_name: "output",
                action_arguments: { host: "galaxy.example.org" },
            },
        });
        expect(wrapper.text()).toContain("This action no longer sends email");
        expect(wrapper.text()).toContain("workflow run form");
        await wrapper.findComponent(GButton).vm.$emit("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted("onChange")).toEqual([[{}]]);
        expect(wrapper.findAllComponents(FormElement)).toHaveLength(1);
    });

    it("hides job-based actions when the step cannot execute them", () => {
        const wrapper = mountFormSection(false);

        expect(wrapper.findAllComponents(FormElement)).toHaveLength(0);
    });
});
