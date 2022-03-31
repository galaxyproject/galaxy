import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormSelect from "./FormSelect";
import Multiselect from "vue-multiselect";
import { BFormRadioGroup } from "bootstrap-vue";
import Vue from "vue";
import flushPromises from "flush-promises";
import { min } from "underscore";

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
    it("Sets no value if optional", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: "",
                defaultValue: "",
                display: null,
                multiple: false,
                optional: true,
                options: [
                    ["test1", "T", false],
                    ["test2", "2", false],
                ],
            },
            localVue,
        });
        expect(wrapper.vm.currentValue).toStrictEqual({ default: false, label: "Nothing selected", value: null });
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
        expect(wrapper.vm.currentValue).toStrictEqual({ label: "test2", value: "2", default: true });
        radio.trigger("click");
        radio.trigger("change");
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
        expect(wrapper.vm.currentValue).toStrictEqual({ label: "test1", value: "T", default: true });
        radio.trigger("click");
        radio.trigger("change");
        await flushPromises();
        expect(wrapper.emitted().input).toEqual([["3"]]);
    });
});

describe("FormSelect", () => {
    // Multiple select, no radio
    it("Nothing selected if no defaults, adds values individaully if selected", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: null,
                defaultValue: null,
                display: null,
                multiple: true,
                optional: true,
                options: [
                    ["test1", "T", false],
                    ["test2", "2", false],
                    ["test3", "3", false],
                ],
            },
            localVue,
        });

        expect(wrapper.vm.currentValue).toStrictEqual(undefined);
        const multiselect = wrapper.findComponent(Multiselect);
        multiselect.vm.select(wrapper.vm.optArray[1]);
        expect(wrapper.emitted().input).toEqual([[["2"]]]);
        multiselect.vm.select(wrapper.vm.optArray[2]);
        expect(wrapper.emitted().input).toEqual([[["2"]], [["3"]]]);
    });
    it("Changes value after new selection is made", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: ["T", "2"],
                defaultValue: ["T", "2"],
                display: null,
                multiple: true,
                options: [
                    ["test1", "T", true],
                    ["test2", "2", true],
                    ["test3", "3", false],
                ],
            },
            localVue,
        });
        expect(wrapper.vm.currentValue).toStrictEqual([
            { label: "test1", value: "T", default: true },
            { label: "test2", value: "2", default: true },
        ]);
    });
});

describe("FormSelect", () => {
    // Multiple select, with checkboxes
    const mountFormSelect = async (props) =>
        await mount(FormSelect, {
            propsData: props,
            localVue,
        });

    it("Changes values to a selected value, and can contain multiple values", async () => {
        const wrapper = await mountFormSelect({
            value: ["T"],
            defaultValue: ["T"],
            display: "checkboxes",
            multiple: true,
            options: [
                ["test1", "T", true],
                ["test2", "2", false],
                ["test3", "3", false],
            ],
        });
        const checkboxes_3 = wrapper.find("input[value='3']");
        const checkboxes_2 = wrapper.find("input[value='2']");
        expect(wrapper.vm.currentValue).toStrictEqual(["T"]);
        checkboxes_2.trigger("click");
        checkboxes_3.trigger("click");
        checkboxes_2.trigger("change");
        checkboxes_3.trigger("change");
        await flushPromises();
        expect(wrapper.emitted().input).toEqual([[["T", "2", "3"]]]);
    });
    it("Has no calue if nothing is selected", async () => {
        const wrapper = await mountFormSelect({
            value: null,
            defaultValue: null,
            display: "checkboxes",
            multiple: true,
            options: [
                ["test1", "T", true],
                ["test2", "2", false],
                ["test3", "3", false],
            ],
        });
        expect(wrapper.vm.currentValue).toStrictEqual(undefined);
    });
});
