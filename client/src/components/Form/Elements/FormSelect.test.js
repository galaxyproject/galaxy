import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormSelect from "./FormSelect";
import Multiselect from "vue-multiselect";
import { BFormRadioGroup } from 'bootstrap-vue';
import Vue from "vue";
import flushPromises from "flush-promises";



const localVue = getLocalVue();

describe("FormSelect", () => {
    // Single select, no radio
    it("Sets default currentValue as first option when not told otherwise", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: "",
                defaultValue: "",
                display: null,
                multiple: false,
                options: [
                    ["test1", "T", false],
                    ["test2", "2", false],
                ],
            },
            localVue,
        });
        expect(wrapper.vm.currentValue).toStrictEqual({ label: "test1", value: "T", default: false });
    });
    it("Sets default currentValue to object with 'default: true' when default not provided from defaultValue", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: "",
                defaultValue: "",
                display: null,
                multiple: false,
                options: [
                    ["test1", "T", false],
                    ["test2", "2", true],
                ],
            },
            localVue,
        });
        expect(wrapper.vm.currentValue).toStrictEqual({ label: "test2", value: "2", default: true });
    });
    it("Sets default from defaultValue", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: "2",
                defaultValue: "2",
                display: null,
                multiple: false,
                options: [
                    ["test1", "T", false],
                    ["test2", "2", false],
                ],
            },
            localVue,
        });
        expect(wrapper.vm.currentValue).toStrictEqual({ label: "test2", value: "2", default: false });
    });
    it("Changes value after new selection is made", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: "T",
                defaultValue: "T",
                display: null,
                multiple: false,
                options: [
                    ["test1", "T", false],
                    ["test2", "2", false],
                ],
            },
            localVue,
        });

        const multiselect = wrapper.findComponent(Multiselect);
        // Manually trigger selection of the second item in optarray in the multiselect
        multiselect.vm.select(wrapper.vm.optArray[1]);
        expect(wrapper.emitted().input).toEqual([["2"]]);
    });
});

describe("FormSelect", () => {
    // Single select, with radio
    const mountFormSelect = async (props) =>
        await mount(FormSelect, {
            propsData: props,
            localVue,
        });

    it("Sets default currentValue as first option when not told otherwise", async () => {
        const wrapper = await mountFormSelect({
                value: "",
                defaultValue: "",
                display: "radio",
                multiple: false,
                options: [
                    ["test1", "T", false],
                    ["test2", "2", false],
                ],
        });
        expect(wrapper.vm.currentValue).toStrictEqual({ label: "test1", value: "T", default: false });
    });
    it("Changes values when selected, and sets from proper default", async () => {
        const wrapper = await mountFormSelect({
            value: "",
            defaultValue: "",
            display: "radio",
            multiple: false,
            options: [
                ["test1", "T", false],
                ["test2", "2", true],
            ],
        });
        const radio = wrapper.find("input[type='radio']");
        expect(wrapper.vm.currentValue).toStrictEqual({label: "test2", value: "2", default: true});
        radio.trigger('click')
        radio.trigger('change')
        await flushPromises();
        expect(wrapper.emitted().input).toEqual([["T"]]);
    });
    it("Changes values to a selected value", async () => {
        const wrapper = await mountFormSelect({
            value: "",
            defaultValue: "",
            display: "radio",
            multiple: false,
            options: [
                ["test1", "T", true],
                ["test2", "2", false],
                ["test3", "3", false],
            ],
        });
        const radio = wrapper.find("input[value='3']");
        expect(wrapper.vm.currentValue).toStrictEqual({label: "test1", value: "T", default: true});
        radio.trigger('click')
        radio.trigger('change')
        await flushPromises();
        expect(wrapper.emitted().input).toEqual([["3"]]);
    });
});

describe("FormSelect", () => {
    // Multiple select, no radio
});

// describe("FormSelect", () => {
//     // Multiple select, with checkboxes
// });