import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./FormSelection.vue";

const localVue = getLocalVue(true);

function createTarget(propsData) {
    const pinia = createTestingPinia();

    return mount(MountTarget, {
        localVue,
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

function testDefaultOptions(wrapper) {
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
        testDefaultOptions(wrapper);
        const noValue = wrapper.find(".multiselect__option--selected");
        expect(noValue.exists()).toBe(false);
        expect(wrapper.emitted().input[0][0]).toBe("value_1");
        await wrapper.setProps({ value: "value_1" });
        const selectedValue = wrapper.find(".multiselect__option--selected");
        expect(selectedValue.text()).toBe("label_1");
    });

    it("optional values", async () => {
        const wrapper = createTarget({
            options: defaultOptions,
            optional: true,
        });
        const target = wrapper.findComponent(MountTarget);
        const options = target.findAll("li > span > div");
        expect(options.length).toBe(5);
        expect(options.at(0).text()).toBe("Nothing selected");
        const selectedDefault = wrapper.find(".multiselect__option--selected");
        expect(selectedDefault.text()).toBe("Nothing selected");
        await wrapper.setProps({ value: "value_1" });
        const selectedValue = wrapper.find(".multiselect__option--selected");
        expect(selectedValue.text()).toBe("label_1");
        options.at(0).trigger("click");
        const nullValue = wrapper.emitted().input[0][0];
        expect(nullValue).toBe(null);
        await wrapper.setProps({ value: null });
        const unselectDefault = wrapper.find(".multiselect__option--selected");
        expect(unselectDefault.text()).toBe("Nothing selected");
    });

    it("multiple values", async () => {
        const wrapper = createTarget({
            optional: true,
            multiple: true,
            options: defaultOptions,
            value: ["value_1", "", 99],
        });
        testDefaultOptions(wrapper);
        const selectedValue = wrapper.findAll(".multiselect__option--selected");
        expect(selectedValue.length).toBe(3);
        expect(selectedValue.at(0).text()).toBe("label_1");
        expect(selectedValue.at(1).text()).toBe("label_3");
        expect(selectedValue.at(2).text()).toBe("label_4");
        selectedValue.at(0).trigger("click");
        const newValue = wrapper.emitted().input[0][0];
        expect(newValue).toEqual(["", 99]);
        await wrapper.setProps({ value: newValue });
        selectedValue.at(1).trigger("click");
        const numericValue = wrapper.emitted().input[1][0];
        expect(numericValue).toEqual([99]);
        await wrapper.setProps({ value: numericValue });
        selectedValue.at(2).trigger("click");
        const nullValue = wrapper.emitted().input[2][0];
        expect(nullValue).toBe(null);
        await wrapper.setProps({ value: nullValue });
        selectedValue.at(0).trigger("click");
        const finalValue = wrapper.emitted().input[3][0];
        expect(finalValue).toEqual(["value_1"]);
    });
});
