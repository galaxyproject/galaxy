import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { PiniaVuePlugin } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./FormData.vue";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

function createTarget(propsData) {
    const pinia = createTestingPinia({ stubActions: false });
    return mount(MountTarget, {
        localVue,
        propsData,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });
}

const defaultOptions = {
    hda: [
        { id: "hda1", hid: 1, name: "hdaName1", src: "hda" },
        { id: "hda2", hid: 2, name: "hdaName2", src: "hda" },
        { id: "hda3", hid: 3, name: "hdaName3", src: "hda" },
    ],
    hdca: [
        { id: "hdca4", hid: 4, name: "hdcaName4", src: "hdca" },
        { id: "hdca5", hid: 5, name: "hdcaName5", src: "hdca" },
    ],
};

const SELECT_OPTIONS = ".multiselect__element";
const SELECTED_VALUE = ".multiselect__option--selected span";

describe("FormData", () => {
    it("regular data", async () => {
        const wrapper = createTarget({
            value: null,
            options: defaultOptions,
        });
        const value_0 = {
            batch: false,
            product: false,
            values: [{ id: "hda3", src: "hda", map_over_type: null }],
        };
        const value_1 = {
            batch: false,
            product: false,
            values: [{ id: "hda1", src: "hda", map_over_type: null }],
        };
        const options = wrapper.find(".btn-group").findAll("button");
        expect(options.length).toBe(4);
        expect(options.at(0).classes()).toContain("active");
        expect(options.at(0).attributes("title")).toBe("Single dataset");
        expect(wrapper.emitted().input[0][0]).toEqual(value_0);
        expect(wrapper.find(SELECTED_VALUE).text()).toEqual("3: hdaName3");
        await wrapper.setProps({ value: value_0 });
        expect(wrapper.emitted().input.length).toEqual(1);
        await wrapper.setProps({ value: { values: [{ id: "hda2", src: "hda" }] } });
        expect(wrapper.find(SELECTED_VALUE).text()).toEqual("2: hdaName2");
        expect(wrapper.emitted().input.length).toEqual(1);
        const elements_0 = wrapper.findAll(SELECT_OPTIONS);
        expect(elements_0.length).toEqual(3);
        await elements_0.at(2).find("span").trigger("click");
        expect(wrapper.emitted().input.length).toEqual(2);
        expect(wrapper.emitted().input[1][0]).toEqual(value_1);
        await wrapper.setProps({ value: value_1 });
        expect(wrapper.find(SELECTED_VALUE).text()).toEqual("1: hdaName1");
    });

    it("optional dataset", async () => {
        const wrapper = createTarget({
            value: null,
            optional: true,
            options: defaultOptions,
        });
        expect(wrapper.emitted().input[0][0]).toEqual(null);
        expect(wrapper.emitted().input.length).toEqual(1);
        expect(wrapper.find(SELECTED_VALUE).text()).toEqual("Nothing selected");
        expect(wrapper.findAll(SELECT_OPTIONS).length).toBe(4);
    });

    it("multiple datasets", async () => {
        const wrapper = createTarget({
            value: {
                values: [
                    { id: "hda2", src: "hda" },
                    { id: "hda3", src: "hda" },
                ],
            },
            multiple: true,
            optional: true,
            options: defaultOptions,
        });
        const options = wrapper.find(".btn-group").findAll("button");
        expect(options.length).toBe(3);
        expect(options.at(0).classes()).toContain("active");
        expect(options.at(0).attributes("title")).toBe("Multiple datasets");
        expect(wrapper.emitted().input[0][0]).toEqual({
            batch: false,
            product: false,
            values: [
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "hda3", map_over_type: null, src: "hda" },
            ],
        });
        expect(wrapper.emitted().input.length).toEqual(1);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(2);
        expect(selectedValues.at(0).text()).toBe("3: hdaName3");
        expect(selectedValues.at(1).text()).toBe("2: hdaName2");
        const value_0 = {
            batch: false,
            product: false,
            values: [
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "hda3", map_over_type: null, src: "hda" },
            ],
        };
        expect(wrapper.emitted().input[0][0]).toEqual(value_0);
        await selectedValues.at(0).trigger("click");
        const value_1 = { batch: false, product: false, values: [{ id: "hda2", map_over_type: null, src: "hda" }] };
        expect(wrapper.emitted().input[1][0]).toEqual(value_1);
        await wrapper.setProps({ value: value_1 });
        await selectedValues.at(1).trigger("click");
        const value_2 = { batch: false, product: false, values: [{ id: "hda2", map_over_type: null, src: "hda" }] };
        expect(wrapper.emitted().input[1][0]).toEqual(value_2);
        await wrapper.setProps({ value: value_2 });
        expect(wrapper.emitted().input.length).toBe(3);
        expect(wrapper.emitted().input[2][0]).toEqual(null);
    });
});
