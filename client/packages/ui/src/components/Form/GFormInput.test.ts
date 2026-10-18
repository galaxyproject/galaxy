import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
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

    it("passes undeclared listeners through to the input", async () => {
        const listeners = { onClick: vi.fn(), onKeyup: vi.fn(), onFocus: vi.fn(), onChange: vi.fn() };
        const Parent = defineComponent({
            setup() {
                return () => h(GFormInput, { modelValue: "", ...listeners });
            },
        });
        const wrapper = mount(Parent, { attachTo: document.body });
        const input = wrapper.find("input");

        await input.trigger("click");
        await input.trigger("keyup", { key: "Enter" });
        await input.trigger("focus");
        await input.trigger("change");

        expect(listeners.onClick).toHaveBeenCalledTimes(1);
        expect(listeners.onKeyup.mock.calls[0]![0]).toBeInstanceOf(KeyboardEvent);
        expect(listeners.onFocus).toHaveBeenCalledTimes(1);
        expect(listeners.onChange).toHaveBeenCalledTimes(1);
        wrapper.unmount();
    });

    it("renders a text input by default and lets a type attribute override it", () => {
        expect(mount(GFormInput).find("input").attributes("type")).toBe("text");

        const password = mount(GFormInput, { attrs: { type: "password" } }).find("input");
        expect(password.attributes("type")).toBe("password");
    });

    it("maps size to a size class instead of the native size attribute", () => {
        const small = mount(GFormInput, { props: { size: "small" } }).find("input");
        expect(small.classes()).toContain("g-small");
        expect(small.attributes("size")).toBeUndefined();

        const large = mount(GFormInput, { props: { size: "large" } }).find("input");
        expect(large.classes()).toContain("g-large");
        expect(mount(GFormInput).find("input").classes()).toEqual(["g-form-input"]);
    });

    it("marks an invalid state with aria-invalid and a state class", () => {
        const invalid = mount(GFormInput, { props: { state: false } }).find("input");
        expect(invalid.attributes("aria-invalid")).toBe("true");
        expect(invalid.classes()).toContain("g-invalid");
        expect(invalid.attributes("state")).toBeUndefined();

        const absent = mount(GFormInput).find("input");
        expect(absent.attributes("aria-invalid")).toBeUndefined();
        expect(absent.classes()).not.toContain("g-invalid");
        expect(absent.classes()).not.toContain("g-valid");

        const valid = mount(GFormInput, { props: { state: true } }).find("input");
        expect(valid.attributes("aria-invalid")).toBeUndefined();
        expect(valid.classes()).toContain("g-valid");

        const unset = mount(GFormInput, { props: { state: null } }).find("input");
        expect(unset.attributes("aria-invalid")).toBeUndefined();
        expect(unset.classes()).toEqual(["g-form-input"]);
    });
});
