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
        await wrapper.setProps({ value: "true" });
        expect(wrapper.emitted().input[0][0]).toBe(true);
        await wrapper.setProps({ value: "false" });
        expect(wrapper.emitted().input[1][0]).toBe(false);
        await wrapper.setProps({ value: true });
        expect(wrapper.emitted().input[2][0]).toBe(true);
        await input.setChecked(false);
        expect(wrapper.emitted().input[3][0]).toBe(false);
        await input.setChecked(true);
        expect(wrapper.emitted().input[4][0]).toBe(true);
    });
});
