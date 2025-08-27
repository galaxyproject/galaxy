import "@/composables/__mocks__/filter";

import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./FormSelection.vue";

function createTarget(propsData) {
    const pinia = createTestingPinia();
    const globalConfig = getLocalVue(true);

    return mount(MountTarget, {
        props: propsData,
        global: {
            ...globalConfig.global,
            plugins: [...(globalConfig.global?.plugins || []), pinia],
        },
    });
}

const defaultOptions = [
    ["label_1", "value_1"],
    ["label_2", "value_2"],
    ["label_3", ""],
    ["label_4", 99],
];

function testDefaultOptions(wrapper) {
    // Test that the component has the correct options through props/computed
    const vm = wrapper.vm;
    expect(vm.options).toBeDefined();
    expect(vm.options.length).toBe(4);
    for (let i = 0; i < vm.options.length; i++) {
        expect(vm.options[i][0]).toBe(`label_${i + 1}`);
    }
}

describe("FormSelect", () => {
    it("basics", async () => {
        const wrapper = createTarget({
            options: defaultOptions,
        });

        // Test that the component has the correct options
        testDefaultOptions(wrapper);

        // Test that it emits the first value by default
        expect(wrapper.emitted().input[0][0]).toBe("value_1");

        // Test multiselect exists
        expect(wrapper.find(".multiselect").exists()).toBe(true);
    });

    it("optional values", async () => {
        const wrapper = createTarget({
            options: defaultOptions,
            optional: true,
        });

        // Test that optional prop is set
        expect(wrapper.vm.optional).toBe(true);

        // Test the computed options include "Nothing selected"
        const computedOptions = wrapper.vm.currentOptions;
        expect(computedOptions).toBeDefined();
        expect(computedOptions.length).toBe(5);
        expect(computedOptions[0].label).toBe("Nothing selected");
        expect(computedOptions[0].value).toBe(null);

        // Test multiselect exists
        expect(wrapper.find(".multiselect").exists()).toBe(true);
    });

    it("multiple values", async () => {
        const wrapper = createTarget({
            optional: true,
            multiple: true,
            options: defaultOptions,
            value: ["value_1", "", 99],
        });

        testDefaultOptions(wrapper);

        // Test that multiple prop is set
        expect(wrapper.vm.multiple).toBe(true);
        expect(wrapper.vm.optional).toBe(true);

        // Test initial value is an array
        expect(Array.isArray(wrapper.vm.value)).toBe(true);
        expect(wrapper.vm.value).toEqual(["value_1", "", 99]);

        // Test multiselect exists
        expect(wrapper.find(".multiselect").exists()).toBe(true);
    });
});
