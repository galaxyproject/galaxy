import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormSelect from "./FormSelect.vue";
import FormSelectOrText from "./FormSelectOrText.vue";

const localVue = getLocalVue();

const OPTIONS = [
    { label: "Nothing", value: null },
    { label: "Apple", value: "apple", help: "Crunchy." },
    { label: "Apple pie", value: "apple pie" },
];

function mountWithValue(value: string | null, validate?: (text: string) => string | undefined): VueWrapper {
    return mount(FormSelectOrText as object, {
        propsData: { id: "fruit", value, options: OPTIONS, otherLabel: "Other fruit...", validate },
        localVue,
    });
}

function selection(wrapper: VueWrapper) {
    return wrapper.find("[data-selected-value]").attributes("data-selected-value");
}

function textField(wrapper: VueWrapper) {
    return wrapper.find("#fruit-other");
}

function emitted(wrapper: VueWrapper) {
    return (wrapper.emitted("input") ?? []).map((args) => args[0]);
}

function lastAlert(wrapper: VueWrapper) {
    const alerts = wrapper.emitted("alert") ?? [];
    return alerts.length ? alerts[alerts.length - 1]![0] : undefined;
}

async function pick(wrapper: VueWrapper, value: string | null) {
    wrapper.findComponent(FormSelect).vm.$emit("input", value);
    await wrapper.vm.$nextTick();
}

async function type(wrapper: VueWrapper, text: string) {
    await textField(wrapper).setValue(text);
}

describe("FormSelectOrText", () => {
    it("shows a listed value in the select", () => {
        const wrapper = mountWithValue("apple");
        expect(selection(wrapper)).toBe("apple");
        expect(textField(wrapper).exists()).toBe(false);
    });

    it("describes the selected option, but not under the text field", async () => {
        const wrapper = mountWithValue("apple");
        expect(wrapper.text()).toContain("Crunchy.");
        await pick(wrapper, "__other__");
        await type(wrapper, "");
        expect(wrapper.text()).not.toContain("Crunchy.");
    });

    it("shows a value the select doesn't list in the text field", () => {
        const wrapper = mountWithValue("banana");
        expect(selection(wrapper)).toBe("__other__");
        expect((textField(wrapper).element as HTMLInputElement).value).toBe("banana");
    });

    it("emits an option picked from the select, including null", async () => {
        const wrapper = mountWithValue("apple");
        await pick(wrapper, "apple pie");
        await pick(wrapper, null);
        expect(emitted(wrapper)).toEqual(["apple pie", null]);
    });

    it("opens the text field with the current value without emitting", async () => {
        const wrapper = mountWithValue("apple");
        await pick(wrapper, "__other__");
        expect((textField(wrapper).element as HTMLInputElement).value).toBe("apple");
        expect(emitted(wrapper)).toEqual([]);
    });

    it("emits typed text and keeps the text field while it passes through a listed value", async () => {
        const wrapper = mountWithValue("banana");
        await type(wrapper, "apple");
        await wrapper.setProps({ value: "apple" });
        expect(textField(wrapper).exists()).toBe(true);
        await type(wrapper, "apple tart");
        expect(emitted(wrapper)).toEqual(["apple", "apple tart"]);
    });

    it("leaves the text field when the value is changed from outside", async () => {
        const wrapper = mountWithValue("banana");
        await wrapper.setProps({ value: "apple pie" });
        expect(selection(wrapper)).toBe("apple pie");
        expect(textField(wrapper).exists()).toBe(false);
    });

    it("doesn't emit empty text and asks for a value", async () => {
        const wrapper = mountWithValue("banana");
        await type(wrapper, "");
        expect(emitted(wrapper)).toEqual([]);
        expect(lastAlert(wrapper)).toBe("Enter a value.");
    });

    it("doesn't emit text that fails validation and alerts until it is fixed", async () => {
        const wrapper = mountWithValue("banana", (text) => (text.includes(" ") ? "No spaces" : undefined));
        await type(wrapper, "blood orange");
        expect(emitted(wrapper)).toEqual([]);
        expect(lastAlert(wrapper)).toBe("No spaces");
        expect(textField(wrapper).classes()).toContain("is-invalid");

        await type(wrapper, "orange");
        expect(emitted(wrapper)).toEqual(["orange"]);
        expect(lastAlert(wrapper)).toBeUndefined();
    });

    it("clears its alert when an option is picked", async () => {
        const wrapper = mountWithValue("banana");
        await type(wrapper, "");
        await pick(wrapper, "apple");
        expect(lastAlert(wrapper)).toBeUndefined();
        expect(textField(wrapper).exists()).toBe(false);
    });
});
