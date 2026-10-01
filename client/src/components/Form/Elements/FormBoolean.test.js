import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { BFormCheckbox } from "bootstrap-vue";
import { beforeEach, describe, expect, it } from "vitest";

import FormBoolean from "./FormBoolean.vue";

const localVue = getLocalVue();

describe("FormBoolean", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormBoolean, {
            props: {
                value: false,
            },
            global: localVue,
        });
    });

    it("check initial value and value change", async () => {
        const switchComponent = wrapper.findComponent(BFormCheckbox);
        const input = wrapper.find("input[type='checkbox']");
        expect(switchComponent.props().checked).toBe(false);
        await wrapper.setProps({ value: "true" });
        expect(emittedArg(wrapper, "input")).toBe(true);
        await wrapper.setProps({ value: "false" });
        expect(emittedArg(wrapper, "input", 1)).toBe(false);
        await wrapper.setProps({ value: true });
        expect(emittedArg(wrapper, "input", 2)).toBe(true);
        await input.setChecked(false);
        expect(emittedArg(wrapper, "input", 3)).toBe(false);
        await input.setChecked(true);
        expect(emittedArg(wrapper, "input", 4)).toBe(true);
    });

    it("renders an unset optional value without changing it", async () => {
        const unset = mount(FormBoolean, { propsData: { value: null }, localVue });
        await unset.vm.$nextTick();
        expect(unset.find("input").element.checked).toBe(false);
        expect(unset.emitted("input")).toBeUndefined();
    });
});
