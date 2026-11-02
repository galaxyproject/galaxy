import "@/composables/__mocks__/filter";

import { createTestingPinia } from "@pinia/testing";
import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import FormSelect from "./FormSelect.vue";
import MountTarget from "./FormSelection.vue";

const localVue = getLocalVue(true);

function createTarget(propsData) {
    const pinia = createTestingPinia({ createSpy: vi.fn });

    return mount(MountTarget, {
        global: localVue,
        propsData,
        pinia,
    });
}

const defaultOptions = [
    ["label_1", "value_1"],
    ["label_2", "value_2"],
    ["label_3", ""],
    ["label_4", 99],
];

// vue-multiselect only renders its option list (and thus the SELECTED_VALUE /
// option-list queries below) while its dropdown is open, so tests need to
// open it before reading those.
async function openMultiselect(wrapper) {
    if (!wrapper.find(".multiselect__content-wrapper").exists()) {
        await wrapper.find(".multiselect__select").trigger("mousedown");
    }
}

async function testDefaultOptions(wrapper) {
    await openMultiselect(wrapper);
    const target = wrapper.findComponent(MountTarget);
    const options = target.findAll("li > span > div");
    expect(options.length).toBe(4);
    for (let i = 0; i < options.length; i++) {
        expect(options.at(i).text()).toBe(`label_${i + 1}`);
    }
}

describe("FormSelect", () => {
    it("basics", async () => {
        const wrapper = createTarget({
            options: defaultOptions,
        });
        await testDefaultOptions(wrapper);
        const noValue = wrapper.find(".multiselect__option--selected");
        expect(noValue.exists()).toBe(false);
        expect(emittedArg(wrapper, "update:modelValue")).toBe("value_1");
        await wrapper.setProps({ modelValue: "value_1" });
        const selectedValue = wrapper.find(".multiselect__option--selected");
        expect(selectedValue.text()).toBe("label_1");
    });

    it("optional values", async () => {
        const wrapper = createTarget({
            options: defaultOptions,
            optional: true,
        });
        await openMultiselect(wrapper);
        const target = wrapper.findComponent(MountTarget);
        const options = target.findAll("li > span > div");
        expect(options.length).toBe(5);
        expect(options.at(0).text()).toBe("Nothing selected");
        const selectedDefault = wrapper.find(".multiselect__option--selected");
        expect(selectedDefault.text()).toBe("Nothing selected");
        await wrapper.setProps({ modelValue: "value_1" });
        const selectedValue = wrapper.find(".multiselect__option--selected");
        expect(selectedValue.text()).toBe("label_1");
        options.at(0).trigger("click");
        const nullValue = emittedArg(wrapper, "update:modelValue");
        expect(nullValue).toBe(null);
        await wrapper.setProps({ modelValue: null });
        // Picking an option closes the dropdown, which removes the option list.
        await openMultiselect(wrapper);
        const unselectDefault = wrapper.find(".multiselect__option--selected");
        expect(unselectDefault.text()).toBe("Nothing selected");
    });

    it("required multi-select emits null when fully cleared", async () => {
        const wrapper = createTarget({
            optional: false,
            multiple: true,
            options: defaultOptions,
            modelValue: ["value_1"],
        });
        await openMultiselect(wrapper);
        const selected = wrapper.findAll(".multiselect__option--selected");
        expect(selected.length).toBe(1);
        selected.at(0).trigger("click");
        const emitted = emittedArg(wrapper, "update:modelValue");
        expect(emitted).toBe(null);
    });

    it("multiple values", async () => {
        const wrapper = createTarget({
            optional: true,
            multiple: true,
            options: defaultOptions,
            modelValue: ["value_1", "", 99],
        });
        await testDefaultOptions(wrapper);
        const selectedValue = wrapper.findAll(".multiselect__option--selected");
        expect(selectedValue.length).toBe(3);
        expect(selectedValue.at(0).text()).toBe("label_1");
        expect(selectedValue.at(1).text()).toBe("label_3");
        expect(selectedValue.at(2).text()).toBe("label_4");
        selectedValue.at(0).trigger("click");
        const newValue = emittedArg(wrapper, "update:modelValue");
        expect(newValue).toEqual(["", 99]);
        await wrapper.setProps({ modelValue: newValue });
        selectedValue.at(1).trigger("click");
        const numericValue = emittedArg(wrapper, "update:modelValue", 1);
        expect(numericValue).toEqual([99]);
        await wrapper.setProps({ modelValue: numericValue });
        selectedValue.at(2).trigger("click");
        const nullValue = emittedArg(wrapper, "update:modelValue", 2);
        expect(nullValue).toBe(null);
        await wrapper.setProps({ modelValue: nullValue });
        selectedValue.at(0).trigger("click");
        const finalValue = emittedArg(wrapper, "update:modelValue", 3);
        expect(finalValue).toEqual(["value_1"]);
    });
});

describe("FormSelect accessible names", () => {
    it("does not name the search input after its id", () => {
        const wrapper = createTarget({ options: defaultOptions });
        const input = wrapper.find("input.multiselect__input");
        expect(input.exists()).toBe(true);
        expect(input.attributes("aria-label")).toBeUndefined();
    });

    it("gives each instance its own default id", () => {
        const options = [{ label: "label_1", value: "value_1" }];
        const ids = [0, 1].map(() => {
            const wrapper = mount(FormSelect, { global: localVue, props: { options } });
            return wrapper.find("input.multiselect__input").attributes("id");
        });
        expect(ids[0]).toMatch(/^form-select-/);
        expect(ids[0]).not.toBe(ids[1]);
    });
});
