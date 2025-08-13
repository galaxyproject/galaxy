import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./WorkflowDisplay";


let axiosMock;

function mountDefault() {
    axiosMock = new MockAdapter(axios);
    const data = {
        name: "workflow_name",
    };
    axiosMock.onGet(`/api/workflows/workflow_id/download?style=preview`).reply(200, data);
    const globalConfig = getLocalVue();
    return mount(MountTarget, {
        props: {
            workflowId: "workflow_id",
            embedded: false,
            expanded: false,
        },
        global: globalConfig.global,
    });
}

function mountError(errContent) {
    axiosMock = new MockAdapter(axios);
    const data = {
        err_msg: errContent,
    };
    axiosMock.onGet(`/api/workflows/workflow_id/download?style=preview`).reply(400, data);
    const globalConfig = getLocalVue();
    return mount(MountTarget, {
        props: {
            workflowId: "workflow_id",
            embedded: false,
            expanded: false,
        },
        global: globalConfig.global,
    });
}

describe("WorkflowDisplay", () => {
    it("basics", async () => {
        const wrapper = mountDefault();
        await flushPromises();
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toContain("Workflow:");
        expect(cardHeader.text()).toContain("workflow_name");
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
        expect(errorContent[0].text()).toBe("firstError: firstValue");
        expect(errorContent[1].text()).toBe("secondError: secondValue");
    });

    it("error message as text", async () => {
        const wrapper = mountError("Something went wrong.");
        await flushPromises();
        // Try different selectors for bootstrap-vue alert
        const alertContent = wrapper.find("[role='alert']");
        if (alertContent.exists()) {
            expect(alertContent.text()).toContain("Something went wrong.");
        } else {
            // Check if the error is displayed differently
            expect(wrapper.text()).toContain("Something went wrong.");
        }
    });
});
