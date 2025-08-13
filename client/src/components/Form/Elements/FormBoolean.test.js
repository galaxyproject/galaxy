import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import FormBoolean from "./FormBoolean";

const globalConfig = getLocalVue();

describe("FormBoolean", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormBoolean, {
            props: {
                value: false,
            },
            global: globalConfig.global,
        });
    });

    it("check initial value and value change", async () => {
        const input = wrapper.find("input");
        const switchComponent = wrapper.findComponent(".custom-switch");
        expect(switchComponent.props().checked).toBe(false);
        await wrapper.setProps({ value: "true" });
        expect(wrapper.emitted().input[0][0]).toBe(true);
        await wrapper.setProps({ value: "false" });
        expect(wrapper.emitted().input[1][0]).toBe(false);
        await wrapper.setProps({ value: true });
        expect(wrapper.emitted().input[2][0]).toBe(true);
        await switchComponent.vm.$emit('input', false);
        expect(wrapper.emitted().input[3][0]).toBe(false);
        await switchComponent.vm.$emit('input', true);
        expect(wrapper.emitted().input[4][0]).toBe(true);
    });
});
