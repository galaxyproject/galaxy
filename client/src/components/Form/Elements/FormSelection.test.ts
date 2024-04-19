import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount, Wrapper } from "@vue/test-utils";

import MountTarget from "./FormSelection.vue";

const localVue = getLocalVue(true);

async function mountFormSelection(propsData: object) {
    const pinia = createTestingPinia();

    return mount(MountTarget as object, {
        localVue,
        propsData,
        pinia,
    });
}

const defaultOptions: [string, string | number][] = [
    ["label_1", ""],
    ["label_2", 99],
    ["label_3", "value_1"],
    ["label_4", "value_2"],
];

function testDefaultOptions(wrapper: Wrapper<Vue>) {
    const target = wrapper.findComponent(MountTarget);
    const options = target.findAll("li > span > span");

    expect(options.length).toBe(4);

    for (let i = 0; i < options.length; i++) {
        expect(options.at(i).text()).toBe(`label_${i + 1}`);
    }
}

describe("FormSelection", () => {
    it("basics", async () => {
        const wrapper = await mountFormSelection({
            options: defaultOptions,
        });

        testDefaultOptions(wrapper);

        const defaultSelected = wrapper.find(".multiselect__option--selected");
        expect(defaultSelected.exists()).toBe(false);

        expect(wrapper.emitted()?.input?.[0]?.[0]).toBe(defaultOptions?.[0]?.[1]);

        for (const option of defaultOptions) {
            await wrapper.setProps({ value: option[1] });

            const selectedValue = wrapper.find(".multiselect__option--selected");
            expect(selectedValue.text()).toBe(option[0]);
        }
    });

    it("optional values", async () => {
        const wrapper = await mountFormSelection({
            options: defaultOptions,
            optional: true,
        });

        const target = wrapper.findComponent(MountTarget);

        const options = target.findAll("li > span > span");
        expect(options.length).toBe(5);
        expect(options.at(0).text()).toBe("Nothing selected");

        const selectedDefault = wrapper.find(".multiselect__option--selected");
        expect(selectedDefault.text()).toBe("Nothing selected");

        await wrapper.setProps({ value: defaultOptions?.[2]?.[1] });

        const selectedValue = wrapper.find(".multiselect__option--selected");
        expect(selectedValue.text()).toBe(defaultOptions?.[2]?.[0]);

        options.at(0).trigger("click");

        const undefinedValue = wrapper.emitted().input?.[0]?.[0];
        expect(undefinedValue).toBe(undefined);

        await wrapper.setProps({ value: undefined });

        const unselectDefault = wrapper.find(".multiselect__option--selected");
        expect(unselectDefault.text()).toBe("Nothing selected");
    });

    it("multiple values", async () => {
        const wrapper = await mountFormSelection({
            optional: true,
            multiple: true,
            options: defaultOptions,
            value: ["value_1", "", 99],
        });

        testDefaultOptions(wrapper);

        const selectedValue = wrapper.findAll(".multiselect__option--selected");
        expect(selectedValue.length).toBe(3);
        expect(selectedValue.at(0).text()).toBe(defaultOptions?.[0]?.[0]);
        expect(selectedValue.at(1).text()).toBe(defaultOptions?.[1]?.[0]);
        expect(selectedValue.at(2).text()).toBe(defaultOptions?.[2]?.[0]);

        selectedValue.at(0).trigger("click");

        const newValue = wrapper.emitted().input?.[0]?.[0];
        expect(newValue).toEqual([defaultOptions?.[1]?.[1], defaultOptions?.[2]?.[1]]);

        await wrapper.setProps({ value: newValue });

        selectedValue.at(1).trigger("click");

        const numericValue = wrapper.emitted().input?.[1]?.[0];
        expect(numericValue).toEqual([defaultOptions?.[2]?.[1]]);

        await wrapper.setProps({ value: numericValue });

        selectedValue.at(2).trigger("click");

        const undefinedValue = wrapper.emitted().input?.[2]?.[0];
        expect(undefinedValue).toBeUndefined();

        await wrapper.setProps({ value: undefinedValue });

        selectedValue.at(0).trigger("click");

        const finalValue = wrapper.emitted().input?.[3]?.[0];

        expect(finalValue).toEqual([defaultOptions?.[0]?.[1], defaultOptions?.[1]?.[1]]);
    });
});
