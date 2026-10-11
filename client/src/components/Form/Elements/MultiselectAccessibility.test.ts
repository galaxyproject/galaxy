import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import Multiselect from "vue-multiselect";

// Exercise Galaxy's dependency patch against the actual multiselect, without a stub.
describe("multiselect accessibility", () => {
    let wrapper: VueWrapper;
    afterEach(() => wrapper?.unmount());

    it("puts combobox state on the focused input and references only mounted options", async () => {
        wrapper = mount(Multiselect, {
            global: getLocalVue(),
            props: {
                id: "selection",
                options: ["Alpha", "Beta"],
                modelValue: "Alpha",
                placeholder: "Choose a dataset",
            },
            attachTo: document.body,
        });
        const input = wrapper.find("input");
        expect(input.attributes("role")).toBe("combobox");
        expect(input.attributes("aria-expanded")).toBe("false");
        expect(input.attributes("aria-controls")).toBeUndefined();
        expect(input.attributes("aria-activedescendant")).toBeUndefined();
        await input.trigger("focus");
        expect(input.attributes("aria-expanded")).toBe("true");
        expect(document.getElementById(input.attributes("aria-controls")!)?.getAttribute("role")).toBe("listbox");
        await input.trigger("keydown", { key: "ArrowDown" });
        expect(document.getElementById(input.attributes("aria-activedescendant")!)?.getAttribute("role")).toBe(
            "option",
        );
        await input.trigger("keyup", { key: "Escape" });
        expect(input.attributes("aria-expanded")).toBe("false");
        expect(input.attributes("aria-controls")).toBeUndefined();
        expect(input.attributes("aria-activedescendant")).toBeUndefined();
    });

    it("uses named native remove buttons in the normal tab order and removes only their selection", async () => {
        wrapper = mount(Multiselect, {
            global: getLocalVue(),
            props: { id: "permissions", options: ["Alpha", "Beta"], modelValue: ["Alpha", "Beta"], multiple: true },
        });
        const buttons = wrapper.findAll("button.multiselect__tag-icon");
        expect(buttons).toHaveLength(2);
        expect(buttons.map((button) => button.attributes("aria-label"))).toEqual(["Remove Alpha", "Remove Beta"]);
        expect(buttons.map((button) => (button.element as HTMLButtonElement).tabIndex)).toEqual([0, 0]);
        expect(buttons.every((button) => button.attributes("type") === "button")).toBe(true);
        await buttons[0]!.trigger("click");
        expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["Beta"]]);
        await wrapper.setProps({ disabled: true });
        expect(wrapper.findAll("button").every((button) => (button.element as HTMLButtonElement).disabled)).toBe(true);
    });
});
