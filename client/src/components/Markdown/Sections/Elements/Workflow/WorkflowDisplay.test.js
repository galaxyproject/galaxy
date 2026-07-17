import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import MountTarget from "./WorkflowDisplay.vue";

const localVue = getLocalVue(true);
const { server, http } = useServerMock();

let getRequests = [];

beforeEach(() => {
    getRequests = [];
});

function mountDefault(data = { name: "workflow_name" }) {
    server.use(
        http.untyped.get("/api/workflows/workflow_id/download", ({ request }) => {
            getRequests.push({ url: request.url });
            return HttpResponse.json(data);
        }),
    );
    return mount(MountTarget, {
        propsData: {
            workflowId: "workflow_id",
            embedded: false,
            expanded: false,
        },
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
        stubs: {
            FontAwesomeIcon: true,
            "b-popover": true,
            "router-link": true,
        },
    });
}

function mountError(errContent) {
    const data = {
        err_msg: errContent,
    };
    server.use(
        http.untyped.get("/api/workflows/workflow_id/download", () => {
            return HttpResponse.json(data, { status: 400 });
        }),
    );
    return mount(MountTarget, {
        propsData: {
            workflowId: "workflow_id",
            embedded: false,
            expanded: false,
        },
        localVue,
    });
}

describe("WorkflowDisplay", () => {
    it("basics", async () => {
        const wrapper = mountDefault();
        await flushPromises();
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBe("Workflow:workflow_name");
        const downloadUrl = wrapper.find("[data-description='workflow download']");
        expect(downloadUrl.attributes("href")).toBe("/api/workflows/workflow_id/download?format=json-download");
        const importUrl = wrapper.find("[data-description='workflow import']");
        expect(importUrl.attributes("href")).toBe("/workflow/imp?id=workflow_id");
        expect(getRequests.length).toBe(1);
        expect(getRequests[0].url).toContain("/api/workflows/workflow_id/download");
        expect(getRequests[0].url).toContain("style=preview");
    });

    it("renders numbered step titles from preview steps", async () => {
        const wrapper = mountDefault({
            name: "workflow_name",
            steps: [
                { order_index: 0, type: "data_input", label: "Input dataset", inputs: [] },
                {
                    order_index: 1,
                    type: "tool",
                    label: "My cool tool",
                    tool_id: "cat1",
                    tool_version: "1.0",
                    inputs: [],
                },
                { order_index: 2, type: "subworkflow", label: "My subworkflow", inputs: [] },
            ],
        });
        await flushPromises();
        const text = wrapper.text();
        expect(text).toContain("Step 1: Input dataset");
        expect(text).toContain("Step 2: My cool tool");
        expect(text).toContain("Step 3: My subworkflow");
        expect(text).not.toContain("NaN");
    });

    it("error message as object", async () => {
        const wrapper = mountError({
            firstError: "firstValue",
            secondError: "secondValue",
        });
        await flushPromises();
        const errorContent = wrapper.findAll("li");
        expect(errorContent.at(0).text()).toBe("firstError: firstValue");
        expect(errorContent.at(1).text()).toBe("secondError: secondValue");
    });

    it("error message as text", async () => {
        const wrapper = mountError("Something went wrong.");
        await flushPromises();
        const errorContent = wrapper.find(".alert > div");
        expect(errorContent.text()).toBe("Something went wrong.");
    });
});
