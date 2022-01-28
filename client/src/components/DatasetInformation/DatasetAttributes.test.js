import Vue from "vue";
import axios from "axios";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import DatasetAttributes from "./DatasetAttributes";
import MockProvider from "../providers/MockProvider";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";

const localVue = getLocalVue();

function buildWrapper(conversion_disable = false) {
    return mount(DatasetAttributes, {
        propsData: {
            datasetId: "dataset_id",
        },
        localVue,
        stubs: {
            DatasetAttributesProvider: MockProvider({
                result: {
                    attribute_inputs: [{ name: "attribute_text", type: "text" }],
                    conversion_inputs: [{ name: "conversion_text", type: "text" }],
                    conversion_disable: conversion_disable,
                    datatype_inputs: [{ name: "datatype_text", type: "text" }],
                    permission_inputs: [{ name: "permission_text", type: "text" }],
                },
            }),
            FontAwesomeIcon: false,
            FormElement: false,
        },
    });
}

describe("DatasetAttributes", () => {
    it("check rendering", async () => {
        const axiosMock = new MockAdapter(axios);
        axiosMock.onPut(`/dataset/set_edit`).reply(200, { message: "success", status: "success" });
        const wrapper = buildWrapper();
        await Vue.nextTick();
        expect(wrapper.findAll("button").length).toBe(6);
        expect(wrapper.findAll("#attribute_text").length).toBe(1);
        expect(wrapper.findAll("#conversion_text").length).toBe(1);
        expect(wrapper.findAll("#datatype_text").length).toBe(1);
        expect(wrapper.findAll("#permission_text").length).toBe(1);
        expect(wrapper.findAll(".tab-pane").length).toBe(4);
        const $button = wrapper.find("#dataset-attributes-default-save");
        await $button.trigger("click");
        await flushPromises();
        expect(wrapper.find("[role=alert]").text()).toBe("success");
    });

    it("check rendering without conversion option", async () => {
        const wrapper = buildWrapper(true);
        await Vue.nextTick();
        expect(wrapper.findAll("button").length).toBe(5);
        expect(wrapper.findAll("#attribute_text").length).toBe(1);
        expect(wrapper.findAll("#conversion_text").length).toBe(0);
        expect(wrapper.findAll("#datatype_text").length).toBe(1);
        expect(wrapper.findAll("#permission_text").length).toBe(1);
        expect(wrapper.findAll(".tab-pane").length).toBe(3);
    });
});
