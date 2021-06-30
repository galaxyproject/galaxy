import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormBoolean from "./FormBoolean";
import Vue from "vue";

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
        expect(wrapper.vm.currentValue).toBe(false);
        wrapper.setProps({ value: true });
        await Vue.nextTick();
        expect(wrapper.vm.currentValue).toBe(true);
        input.trigger("click");
        expect(input.element.checked).toBe(false);
        input.trigger("click");
        expect(input.element.checked).toBe(true);
        expect(wrapper.emitted().input[0][0]).toBe(true);
    });
});
