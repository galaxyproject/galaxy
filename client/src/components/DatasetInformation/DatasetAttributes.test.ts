import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import DatasetAttributes from "./DatasetAttributes.vue";

const DATASET_ID = "dataset_id";

const localVue = getLocalVue();
const { server, http } = useServerMock();

async function mountDatasetAttributes(conversion_disable = false) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    server.use(
        http.untyped.put("/dataset/set_edit", () => {
            return HttpResponse.json({ message: "success", status: "success" });
        }),
        http.untyped.get("/dataset/get_edit", ({ request }) => {
            const url = new URL(request.url);
            if (url.searchParams.get("dataset_id") === DATASET_ID) {
                return HttpResponse.json({
                    attribute_inputs: [{ name: "attribute_text", type: "text" }],
                    conversion_inputs: [{ name: "conversion_text", type: "text" }],
                    conversion_disable: conversion_disable,
                    datatype_inputs: [{ name: "datatype_text", type: "text" }],
                    permission_inputs: [{ name: "permission_text", type: "text" }],
                });
            }
            return HttpResponse.json({}, { status: 404 });
        }),
    );

    const wrapper = mount(DatasetAttributes as object, {
        props: {
            datasetId: DATASET_ID,
        },
        global: localVue,
        pinia,
    });

    await flushPromises();

    return wrapper;
}

async function buildWrapperWithError(error: string) {
    server.use(
        http.untyped.get("/dataset/get_edit", () => {
            return HttpResponse.json({}, { status: 400 });
        }),
    );
    const wrapper = mount(DatasetAttributes as object, {
        props: {
            datasetId: DATASET_ID,
            messageText: error,
            messageVariant: "danger",
        },
        global: localVue,
        stubs: {
            FontAwesomeIcon: false,
            FormElement: false,
        },
    });
    await flushPromises();
    return wrapper;
}

describe("DatasetAttributes", () => {
    it("check rendering", async () => {
        const wrapper = await mountDatasetAttributes();

        expect(wrapper.findAll("button").length).toBe(6);
        expect(wrapper.findAll("#attribute_text").length).toBe(1);
        expect(wrapper.findAll("#conversion_text").length).toBe(1);
        expect(wrapper.findAll("#datatype_text").length).toBe(1);
        expect(wrapper.findAll("#permission_text").length).toBe(1);
        expect(wrapper.findAll(".tab-pane").length).toBe(3);
        expect(wrapper.findAll(".ui-portlet-section").length).toBe(2);

        const saveButton = wrapper.find("#dataset-attributes-default-save");

        await saveButton.trigger("click");

        await flushPromises();

        expect(wrapper.find("[role=alert]").text()).toBe("success");
    });

    it("check rendering without conversion option", async () => {
        const wrapper = await mountDatasetAttributes(true);

        expect(wrapper.findAll("button").length).toBe(5);
        expect(wrapper.findAll("#attribute_text").length).toBe(1);
        expect(wrapper.findAll("#conversion_text").length).toBe(0);
        expect(wrapper.findAll("#datatype_text").length).toBe(1);
        expect(wrapper.findAll("#permission_text").length).toBe(1);
        expect(wrapper.findAll(".tab-pane").length).toBe(3);
        expect(wrapper.findAll(".ui-portlet-section").length).toBe(1);
    });

    it("doesn't render edit controls with error", async () => {
        const wrapper = await buildWrapperWithError("error");
        expect(wrapper.findAll("button").length).toBe(0);
        expect(wrapper.findAll("#attribute_text").length).toBe(0);
        expect(wrapper.findAll("#conversion_text").length).toBe(0);
        expect(wrapper.findAll("#datatype_text").length).toBe(0);
        expect(wrapper.findAll("#permission_text").length).toBe(0);
        expect(wrapper.findAll(".tab-pane").length).toBe(0);
        expect(wrapper.findAll(".ui-portlet-section").length).toBe(0);
    });
});
