import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { ToolOutputActions, ToolOutputPreview, ToolOutputsPreviewRequest } from "@/api/tools";

import ToolFormOutputs from "./ToolFormOutputs.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();

const REQUEST: ToolOutputsPreviewRequest = {
    tool_id: "sort1",
    tool_version: "1.0",
    history_id: "history1",
    inputs: { input: { src: "hda", id: "hda1" } },
    strict: true,
};

function previewOutput(name: string, fields: Partial<ToolOutputPreview> = {}): ToolOutputPreview {
    return {
        name,
        label: `${name} on data 1`,
        output_type: "data",
        format: "tabular",
        hidden: false,
        dynamic: false,
        mapped_over: false,
        ...fields,
    };
}

function actions(fields: Partial<ToolOutputActions> = {}): ToolOutputActions {
    return { rename: null, add_tags: [], remove_tags: [], hide: false, ...fields };
}

describe("ToolFormOutputs", () => {
    let previewRequests: ToolOutputsPreviewRequest[];

    function usePreviewResponse(outputs: ToolOutputPreview[]) {
        server.use(
            http.post("/api/tools/outputs_preview", async ({ request, response }) => {
                previewRequests.push((await request.json()) as ToolOutputsPreviewRequest);
                return response(200).json({ supported: true, unsupported_reason: null, job_count: 1, outputs });
            }),
        );
    }

    function mountOutputs(modelValue: Record<string, ToolOutputActions> = {}) {
        return mount(ToolFormOutputs, {
            props: { request: REQUEST, modelValue },
            localVue,
        });
    }

    async function openSection(wrapper: ReturnType<typeof mountOutputs>) {
        await wrapper.find("[data-description='tool form outputs'] h3").trigger("click");
        await flushPromises();
    }

    function outputNames(wrapper: ReturnType<typeof mountOutputs>) {
        return wrapper.findAll(".tool-form-output").map((row) => row.attributes("data-output-name"));
    }

    function lastEmitted(wrapper: ReturnType<typeof mountOutputs>) {
        const emitted = wrapper.emitted("update:modelValue") ?? [];
        return emitted[emitted.length - 1]?.[0];
    }

    beforeEach(() => {
        setActivePinia(createPinia());
        previewRequests = [];
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("asks for the preview only once the section is opened", async () => {
        usePreviewResponse([previewOutput("out_file1")]);
        const wrapper = mountOutputs();
        await flushPromises();
        expect(previewRequests).toEqual([]);

        await openSection(wrapper);

        expect(previewRequests).toEqual([REQUEST]);
        expect(outputNames(wrapper)).toEqual(["out_file1"]);
    });

    it("opens with the preview when it starts with changes, as on a rerun", async () => {
        usePreviewResponse([previewOutput("out_file1")]);
        const wrapper = mountOutputs({ out_file1: actions({ hide: true }) });
        await flushPromises();

        expect(previewRequests).toEqual([REQUEST]);
        expect(outputNames(wrapper)).toEqual(["out_file1"]);
    });

    it("emits the new name typed for an output", async () => {
        usePreviewResponse([previewOutput("out_file1"), previewOutput("out_file2")]);
        const wrapper = mountOutputs();
        await openSection(wrapper);

        await wrapper.find("input#tool-form-output-out_file2-rename").setValue("sorted");

        expect(lastEmitted(wrapper)).toEqual({ out_file2: actions({ rename: "sorted" }) });
    });

    it("hides an output with its hide button", async () => {
        usePreviewResponse([previewOutput("out_file1")]);
        const wrapper = mountOutputs();
        await openSection(wrapper);

        await wrapper.find("[data-description='output hide']").trigger("click");

        expect(lastEmitted(wrapper)).toEqual({ out_file1: actions({ hide: true }) });
    });

    it("leaves out an output once its changes are cleared", async () => {
        usePreviewResponse([previewOutput("out_file1")]);
        const wrapper = mountOutputs({ out_file1: actions({ rename: "sorted" }) });
        await flushPromises();

        await wrapper.find("input#tool-form-output-out_file1-rename").setValue("");

        expect(lastEmitted(wrapper)).toEqual({});
    });

    it("drops the changes of outputs the run no longer creates", async () => {
        usePreviewResponse([previewOutput("out_file1")]);
        const wrapper = mountOutputs({ out_file1: actions({ hide: true }), filtered: actions({ hide: true }) });
        await flushPromises();

        expect(lastEmitted(wrapper)).toEqual({ out_file1: actions({ hide: true }) });
    });

    it("drops the changes of outputs a changed form no longer creates while the section is closed", async () => {
        usePreviewResponse([previewOutput("out_file1")]);
        const wrapper = mountOutputs({ out_file1: actions({ hide: true }), out_file2: actions({ hide: true }) });
        await flushPromises();
        await openSection(wrapper);
        await wrapper.setProps({ modelValue: { out_file2: actions({ hide: true }) } });
        vi.useFakeTimers();
        const changed = { ...REQUEST, tool_version: "2.0" };

        await wrapper.setProps({ request: changed });
        await vi.advanceTimersByTimeAsync(300);
        await flushPromises();

        expect(previewRequests).toEqual([REQUEST, changed]);
        expect(lastEmitted(wrapper)).toEqual({});
    });

    it("asks again after the form changes, once it settles", async () => {
        usePreviewResponse([previewOutput("out_file1")]);
        const wrapper = mountOutputs();
        await openSection(wrapper);
        vi.useFakeTimers();
        const changed = { ...REQUEST, inputs: { input: { src: "hda", id: "hda2" } } };

        await wrapper.setProps({ request: changed });
        await wrapper.setProps({ request: { ...changed } });
        await vi.advanceTimersByTimeAsync(300);
        await flushPromises();

        expect(previewRequests).toEqual([REQUEST, changed]);
    });

    it("says so when the settings filter out every output", async () => {
        usePreviewResponse([]);
        const wrapper = mountOutputs();

        await openSection(wrapper);

        expect(wrapper.find("[data-description='outputs preview empty']").exists()).toBe(true);
        expect(outputNames(wrapper)).toEqual([]);
    });

    it("shows why the outputs of a tool can't be described", async () => {
        server.use(
            http.post("/api/tools/outputs_preview", ({ response }) =>
                response(200).json({ supported: false, unsupported_reason: "Reason from the server.", job_count: 0 }),
            ),
        );
        const wrapper = mountOutputs();

        await openSection(wrapper);

        expect(wrapper.find("[data-description='outputs preview unsupported']").text()).toBe("Reason from the server.");
        expect(outputNames(wrapper)).toEqual([]);
    });

    it("lets the changes of a rerun be cleared when the outputs can't be described", async () => {
        server.use(
            http.post("/api/tools/outputs_preview", ({ response }) =>
                response(200).json({ supported: false, unsupported_reason: "Reason from the server.", job_count: 0 }),
            ),
        );
        const wrapper = mountOutputs({ out_file1: actions({ hide: true }) });
        await flushPromises();

        await wrapper.find("[data-description='outputs clear changes']").trigger("click");

        expect(lastEmitted(wrapper)).toEqual({});
    });

    it("keeps the form usable when the inputs are not complete yet", async () => {
        server.use(
            http.post("/api/tools/outputs_preview", () =>
                HttpResponse.json({ err_msg: "Parameter 'input' is required.", err_code: 400008 }, { status: 400 }),
            ),
        );
        const wrapper = mountOutputs();

        await openSection(wrapper);

        expect(wrapper.find("[data-description='outputs preview error']").exists()).toBe(true);
        expect(outputNames(wrapper)).toEqual([]);
    });
});
