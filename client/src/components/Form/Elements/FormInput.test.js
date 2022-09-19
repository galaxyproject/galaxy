import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormInput from "./FormInput";

const localVue = getLocalVue();

describe("FormInput", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormInput, {
            propsData: {
                id: "input",
                value: "initial_value",
            },
            localVue,
        });
    });

    it("check initial value and value change", async () => {
        const input = wrapper.find("input");
        expect(input.element.value).toBe("initial_value");
        await input.setValue("new_value");
        expect(input.element.value).toBe("new_value");
        expect(wrapper.emitted().input[0][0]).toBe("new_value");
    });

    it("check switching to text area", async () => {
        await wrapper.setProps({ area: true });
        const input = wrapper.find("textarea");
        expect(input.element.value).toBe("initial_value");
        await input.setValue("new_value");
        expect(input.element.value).toBe("new_value");
        expect(wrapper.emitted().input[0][0]).toBe("new_value");
    });
});
