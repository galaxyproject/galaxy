import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormBoolean from "./FormBoolean.vue";

const localVue = getLocalVue();

function mountFormBoolean(props, attrs = {}) {
    return mount(FormBoolean, { props, attrs, global: localVue });
}

describe("FormBoolean", () => {
    it("check initial value and value change", async () => {
        const wrapper = mountFormBoolean({ modelValue: false });
        const input = wrapper.find("input[type='checkbox']");
        expect(input.element.checked).toBe(false);
        await wrapper.setProps({ modelValue: "true" });
        expect(input.element.checked).toBe(true);
        await wrapper.setProps({ modelValue: "false" });
        expect(input.element.checked).toBe(false);
        await wrapper.setProps({ modelValue: true });
        expect(input.element.checked).toBe(true);
        expect(wrapper.emitted("update:modelValue")).toBeUndefined();
        await input.setValue(false);
        expect(emittedArg(wrapper, "update:modelValue")).toBe(false);
        await wrapper.setProps({ modelValue: emittedArg(wrapper, "update:modelValue") });
        expect(input.element.checked).toBe(false);
        await input.setValue(true);
        expect(emittedArg(wrapper, "update:modelValue", 1)).toBe(true);
    });

    it("renders a Yes/No switch with the parameter id on its input", async () => {
        const wrapper = mountFormBoolean({ modelValue: true }, { id: "param" });
        const input = wrapper.find("input[type='checkbox']");
        expect(input.attributes("id")).toBe("param");
        expect(input.attributes("role")).toBe("switch");
        expect(wrapper.classes()).toContain("no-highlight");
        expect(wrapper.find(".g-checkbox-label").text()).toBe("Yes");
        await wrapper.setProps({ modelValue: false });
        expect(wrapper.find(".g-checkbox-label").text()).toBe("No");
    });

    it("renders no label when noLabel is set", () => {
        const wrapper = mountFormBoolean({ modelValue: true, noLabel: true });
        expect(wrapper.find(".g-checkbox-label").exists()).toBe(false);
    });

    it("renders an unset optional value without changing it", async () => {
        const wrapper = mountFormBoolean({ modelValue: null });
        await wrapper.vm.$nextTick();
        expect(wrapper.find("input").element.checked).toBe(false);
        expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    });
});
