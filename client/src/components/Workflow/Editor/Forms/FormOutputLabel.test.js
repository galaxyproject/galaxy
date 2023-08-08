import { mount } from "@vue/test-utils";
import { createPinia, PiniaVuePlugin, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useWorkflowStepStore } from "@/stores/workflowStepStore";

import FormOutputLabel from "./FormOutputLabel";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

describe("FormOutputLabel", () => {
    let wrapper;
    let wrapperOther;
    let stepStore;
    const outputs = [
        { name: "output-name", label: "output-label" },
        { name: "other-name", label: "other-label" },
    ];

    beforeEach(() => {
        const stepOne = { id: 0, outputs: [{ name: "output-name" }], workflow_outputs: outputs };
        const pinia = createPinia();
        setActivePinia(pinia);
        wrapper = mount(FormOutputLabel, {
            propsData: {
                name: "output-name",
                step: stepOne,
            },
            localVue,
            pinia,
            provide: { workflowId: "mock-workflow" },
        });

        const stepTwo = { id: 1, outputs: [{ name: "other-name" }], workflow_outputs: outputs };
        wrapperOther = mount(FormOutputLabel, {
            propsData: {
                name: "other-name",
                step: stepTwo,
            },
            localVue,
            pinia,
            provide: { workflowId: "mock-workflow" },
        });
        stepStore = useWorkflowStepStore("mock-workflow");
        stepStore.addStep(stepOne);
        stepStore.addStep(stepTwo);
    });

    it("check initial value and value change", async () => {
        const title = wrapper.find(".ui-form-title-text");
        expect(title.text()).toBe("Label");
        await wrapper.setProps({ showDetails: true });
        expect(title.text()).toBe("Label for: 'output-name'");
        const input = wrapper.find("input");
        const inputOther = wrapperOther.find("input");
        await input.setValue("new-label");
        expect(wrapper.find(".ui-form-error").exists()).toBe(false);
        expect(wrapperOther.find(".ui-form-error").exists()).toBe(false);
        await inputOther.setValue("other-label");
        expect(wrapper.find(".ui-form-error").exists()).toBe(false);
        expect(wrapperOther.find(".ui-form-error").exists()).toBe(false);
        await input.setValue("other-label");
        expect(wrapper.find(".ui-form-error").text()).toBe("Duplicate output label 'other-label' will be ignored.");
        expect(wrapperOther.find(".ui-form-error").exists()).toBe(false);
        expect(stepStore.workflowOutputs["new-label"].outputName).toBe("output-name");
    });
});
