import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import MockProvider from "@/components/providers/MockProvider";

import DatasetAttributes from "./DatasetAttributes.vue";

const localVue = getLocalVue();

async function buildWrapper(conversion_disable = false) {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    const wrapper = mount(DatasetAttributes as object, {
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
        pinia,
    });

    await flushPromises();

    return wrapper;
}

describe("DatasetAttributes", () => {
    it("check rendering", async () => {
        const axiosMock = new MockAdapter(axios);
        axiosMock.onPut(`/dataset/set_edit`).reply(200, { message: "success", status: "success" });

        const wrapper = await buildWrapper();

        expect(wrapper.findAll("button").length).toBe(6);
        expect(wrapper.findAll("#attribute_text").length).toBe(1);
        expect(wrapper.findAll("#conversion_text").length).toBe(1);
        expect(wrapper.findAll("#datatype_text").length).toBe(1);
        expect(wrapper.findAll("#permission_text").length).toBe(1);
        expect(wrapper.findAll(".tab-pane").length).toBe(3);
        expect(wrapper.findAll(".ui-portlet-section").length).toBe(2);

        const $button = wrapper.find("#dataset-attributes-default-save");

        await $button.trigger("click");
        await flushPromises();

        expect(wrapper.find("[role=alert]").text()).toBe("success");
    });

    it("check rendering without conversion option", async () => {
        const wrapper = await buildWrapper(true);

        expect(wrapper.findAll("button").length).toBe(5);
        expect(wrapper.findAll("#attribute_text").length).toBe(1);
        expect(wrapper.findAll("#conversion_text").length).toBe(0);
        expect(wrapper.findAll("#datatype_text").length).toBe(1);
        expect(wrapper.findAll("#permission_text").length).toBe(1);
        expect(wrapper.findAll(".tab-pane").length).toBe(3);
        expect(wrapper.findAll(".ui-portlet-section").length).toBe(1);
    });
});
