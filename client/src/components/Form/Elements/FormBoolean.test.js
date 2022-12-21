import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import FormBoolean from "./FormBoolean";

const localVue = getLocalVue();

describe("FormBoolean", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormBoolean, {
            propsData: {
                value: false,
            },
            localVue,
        });
    });

    it("check initial value and value change", async () => {
        const input = wrapper.find("input");
        const switchComponent = wrapper.findComponent(".custom-switch");

        expect(switchComponent.props().value).toBe(false);

        await wrapper.setProps({ value: true });
        expect(switchComponent.props().value).toBe(true);

        await input.trigger("click");
        expect(input.element.checked).toBe(false);

        await input.trigger("click");
        expect(input.element.checked).toBe(true);
        expect(wrapper.emitted().input[0][0]).toBe(true);
    });
});
