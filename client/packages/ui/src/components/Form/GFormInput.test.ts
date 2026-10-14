import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, ref } from "vue";

import GFormInput from "./GFormInput.vue";

function mountWithModel(initial: string | null) {
    const text = ref(initial);
    const Parent = defineComponent({
        setup() {
            return () =>
                h(GFormInput, {
                    modelValue: text.value,
                    "onUpdate:modelValue": (value: string | null) => (text.value = value),
                });
        },
    });
    return { text, wrapper: mount(Parent, { attachTo: document.body }) };
}

describe("GFormInput", () => {
    it("receives the bound value as modelValue", () => {
        const { wrapper } = mountWithModel("hello");
        const input = wrapper.findComponent(GFormInput);

        expect(input.props("modelValue")).toBe("hello");
        expect((wrapper.find("input").element as HTMLInputElement).value).toBe("hello");
        wrapper.unmount();
    });

    it("updates the bound value on input", async () => {
        const { text, wrapper } = mountWithModel("");

        await wrapper.find("input").setValue("typed");
        expect(text.value).toBe("typed");
        expect(wrapper.findComponent(GFormInput).emitted("update:modelValue")).toEqual([["typed"]]);
        wrapper.unmount();
    });

    it("re-emits keydown and blur, and focuses through the exposed method", async () => {
        const { wrapper } = mountWithModel("");
        const component = wrapper.findComponent(GFormInput);
        const input = wrapper.find("input");

        await input.trigger("keydown", { key: "Escape" });
        expect(component.emitted("keydown")![0]![0]).toBeInstanceOf(KeyboardEvent);

        (component.vm as unknown as { focus: () => void }).focus();
        expect(document.activeElement).toBe(input.element);

        await input.trigger("blur");
        expect(component.emitted("blur")).toHaveLength(1);
        wrapper.unmount();
    });
});
