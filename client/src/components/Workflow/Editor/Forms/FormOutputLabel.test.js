import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormOutputLabel from "./FormOutputLabel";
import { ActiveOutputs } from "components/Workflow/Editor/modules/outputs";

const localVue = getLocalVue();

describe("FormOutputLabel", () => {
    let wrapper;
    let wrapperOther;
    const activeOutputs = new ActiveOutputs();
    const outputs = [
        { name: "output-name", label: "output-label" },
        { name: "other-name", label: "other-label" },
    ];

    beforeEach(() => {
        activeOutputs.initialize(outputs);
        wrapper = mount(FormOutputLabel, {
            propsData: {
                name: "output-name",
                activeOutputs: activeOutputs,
            },
            localVue,
        });
        wrapperOther = mount(FormOutputLabel, {
            propsData: {
                name: "other-name",
                activeOutputs: activeOutputs,
            },
            localVue,
        });
    });

    it("check initial value and value change", async () => {
        const title = wrapper.find(".ui-form-title-text");
        expect(title.text()).toBe("Label");
        await wrapper.setProps({ showDetails: true });
        expect(title.text()).toBe("Label for: 'output-name'");
        const input = wrapper.find("input");
        const inputOther = wrapperOther.find("input");
        await input.setValue("new-label");
        expect(wrapper.vm.error).toBe(null);
        expect(activeOutputs.get("output-name").label).toBe("new-label");
        await inputOther.setValue("other-label");
        await input.setValue("other-label");
        expect(wrapper.vm.error).toBe("Duplicate output label 'other-label' will be ignored.");
        expect(activeOutputs.get("output-name").label).toBe("new-label");
    });
});
