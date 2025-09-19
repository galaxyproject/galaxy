import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./WorkflowDisplay";

const localVue = getLocalVue(true);

let axiosMock;

function mountDefault() {
    axiosMock = new MockAdapter(axios);
    const data = {
        name: "workflow_name",
    };
    axiosMock.onGet(`/api/workflows/workflow_id/download?style=preview`).reply(200, data);
    return mount(MountTarget, {
        propsData: {
            workflowId: "workflow_id",
            embedded: false,
            expanded: false,
        },
        localVue,
    });
}

function mountError(errContent) {
    axiosMock = new MockAdapter(axios);
    const data = {
        err_msg: errContent,
    };
    axiosMock.onGet(`/api/workflows/workflow_id/download?style=preview`).reply(400, data);
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
        expect(cardHeader.text()).toBe("Workflow: workflow_name");
        const downloadUrl = wrapper.find("[data-description='workflow download']");
        expect(downloadUrl.attributes("href")).toBe("/api/workflows/workflow_id/download?format=json-download");
        const importUrl = wrapper.find("[data-description='workflow import']");
        expect(importUrl.attributes("href")).toBe("/workflow/imp?id=workflow_id");
        const dataRequest = axiosMock.history.get[0].url;
        expect(dataRequest).toBe("/api/workflows/workflow_id/download?style=preview");
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
