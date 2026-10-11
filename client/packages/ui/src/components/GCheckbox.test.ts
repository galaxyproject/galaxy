import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, ref } from "vue";

import GCheckbox from "./GCheckbox.vue";

function mountWithModel(initial: boolean) {
    const checked = ref(initial);
    const Parent = defineComponent({
        setup() {
            return () =>
                h(GCheckbox, {
                    id: "test-checkbox",
                    modelValue: checked.value,
                    "onUpdate:modelValue": (value: boolean) => (checked.value = value),
                });
        },
    });
    return { checked, wrapper: mount(Parent) };
}

describe("GCheckbox", () => {
    it("receives the bound value as modelValue", () => {
        const { wrapper } = mountWithModel(true);
        const checkbox = wrapper.findComponent(GCheckbox);

        expect(checkbox.props("modelValue")).toBe(true);
        expect(checkbox.attributes("value")).toBeUndefined();
        expect((wrapper.find("input").element as HTMLInputElement).checked).toBe(true);
    });

    it("updates the bound value when toggled", async () => {
        const { checked, wrapper } = mountWithModel(false);

        await wrapper.find("input").setValue(true);
        expect(checked.value).toBe(true);
        expect(wrapper.findComponent(GCheckbox).emitted("update:modelValue")).toEqual([[true]]);

        await wrapper.find("input").setValue(false);
        expect(checked.value).toBe(false);
    });

    it("emits change with the native event", async () => {
        const { wrapper } = mountWithModel(false);

        await wrapper.find("input").setValue(true);
        const change = wrapper.findComponent(GCheckbox).emitted("change");
        expect(change).toHaveLength(1);
        expect(change![0]![0]).toBeInstanceOf(Event);
    });

    it("shows a partly-checked state while indeterminate", async () => {
        const wrapper = mount(GCheckbox, { props: { indeterminate: true } });
        const input = wrapper.get("input").element as HTMLInputElement;

        expect(input.indeterminate).toBe(true);

        await wrapper.setProps({ indeterminate: false });
        expect(input.indeterminate).toBe(false);
    });

    it("renders as a switch in toggle mode", () => {
        const wrapper = mount(GCheckbox, { props: { modelValue: false, toggle: true } });

        expect(wrapper.classes()).toContain("g-switch");
        expect(wrapper.find(".g-switch-slider").exists()).toBe(true);
    });
});
