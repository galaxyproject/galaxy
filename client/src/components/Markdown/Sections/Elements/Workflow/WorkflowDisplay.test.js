import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import MountTarget from "./WorkflowDisplay.vue";

const localVue = getLocalVue(true);
const { server, http } = useServerMock();

let getRequests = [];

beforeEach(() => {
    getRequests = [];
});

function mountDefault() {
    const data = {
        name: "workflow_name",
    };
    server.use(
        http.untyped.get("/api/workflows/workflow_id/download", ({ request }) => {
            getRequests.push({ url: request.url });
            return HttpResponse.json(data);
        }),
    );
    return mount(MountTarget, {
        props: {
            workflowId: "workflow_id",
            embedded: false,
            expanded: false,
        },
        global: localVue,
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
        props: {
            workflowId: "workflow_id",
            embedded: false,
            expanded: false,
        },
        global: localVue,
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
