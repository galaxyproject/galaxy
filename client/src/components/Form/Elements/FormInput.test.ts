import { getLocalVue } from "@tests/jest/helpers";
import { mount, Wrapper } from "@vue/test-utils";

import FormInput from "./FormInput.vue";

const localVue = getLocalVue();

describe("FormInput", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        wrapper = mount(FormInput as object, {
            propsData: {
                id: "input",
                value: "initial_value",
            },
            localVue,
        });
    });

    it("check initial value and value change", async () => {
        const input = wrapper.find("input");
        expect((input.element as HTMLInputElement).value).toBe("initial_value");

        await input.setValue("new_value");

        expect((input.element as HTMLInputElement).value).toBe("new_value");
        expect(wrapper.emitted().input?.[0]?.[0]).toBe("new_value");
    });

    it("check switching to text area", async () => {
        await wrapper.setProps({ area: true });

        const input = wrapper.find("textarea");
        expect((input.element as HTMLInputElement).value).toBe("initial_value");

        await input.setValue("new_value");

        expect((input.element as HTMLInputElement).value).toBe("new_value");
        expect(wrapper.emitted().input?.[0]?.[0]).toBe("new_value");
    });
});
