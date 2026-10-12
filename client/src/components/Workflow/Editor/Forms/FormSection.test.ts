import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { DataOutput, Step } from "@/stores/workflowStepStore";

import FormSection from "./FormSection.vue";
import FormElement from "@/components/Form/FormElement.vue";

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

function mountFormSection(supportsJobBasedActions?: boolean) {
    return shallowMount(FormSection, {
        global: localVue,
        props: {
            id: 0,
            nodeInputs: [],
            // Children are stubbed; this boundary only reads the output name and step identity.
            nodeOutputs: [{ name: "output" } satisfies Pick<DataOutput, "name">],
            step: { id: 0, type: "pick_value" } satisfies Pick<Step, "id" | "type">,
            datatypes: [],
            postJobActions: {},
            supportsJobBasedActions,
        },
    });
}

describe("FormSection", () => {
    it("shows job-based actions by default", () => {
        const wrapper = mountFormSection();

        const actions = wrapper.findAllComponents(FormElement);
        expect(actions).toHaveLength(2);
        expect(actions.map((action) => action.props("title"))).toEqual(["Email notification", "Output cleanup"]);
    });

    it("hides job-based actions when the step cannot execute them", () => {
        const wrapper = mountFormSection(false);

        expect(wrapper.findAllComponents(FormElement)).toHaveLength(0);
    });
});
