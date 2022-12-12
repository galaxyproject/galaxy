import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import MountTarget from "./WorkflowDisplay";

const localVue = getLocalVue(true);

describe("WorkflowDisplay", () => {
    let wrapper;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        const data = {};
        axiosMock.onGet(`/api/workflows/workflow_id/download?style=preview`).reply(200, data);
        wrapper = mount(MountTarget, {
            propsData: {
                args: {
                    workflow_id: "workflow_id",
                },
                embedded: false,
                expanded: false,
            },
            localVue,
        });
    });

    afterEach(() => {
        axiosMock.reset();
    });

    it("basics", async () => {
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBe("Workflow:");
        const downloadUrl = wrapper.find("[data-description='workflow download']");
        expect(downloadUrl.attributes("href")).toBe("/api/workflows/workflow_id/download?format=json-download");
        const importUrl = wrapper.find("[data-description='workflow import']");
        expect(importUrl.attributes("href")).toBe("/workflow/imp?id=workflow_id");
        const dataRequest = axiosMock.history.get[0].url;
        expect(dataRequest).toBe("/api/workflows/workflow_id/download?style=preview");
    });
});
