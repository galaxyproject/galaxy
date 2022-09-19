import InteractiveTools from "./InteractiveTools";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import flushPromises from "flush-promises";
import testInteractiveToolsResponse from "./testData/testInteractiveToolsResponse";

import MockAdapter from "axios-mock-adapter";
import axios from "axios";

describe("InteractiveTools/InteractiveTools.vue", () => {
    const localVue = getLocalVue();
    let wrapper;
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet("/api/entry_points?running=true").reply(200, testInteractiveToolsResponse);
        axiosMock.onDelete(new RegExp("/api/entry_points/*")).reply(200, { status: "ok", message: "ok" });
        wrapper = mount(InteractiveTools, {
            computed: {
                currentHistory() {
                    return {
                        loadCurrentHistory() {},
                    };
                },
            },
            localVue,
        });

        await flushPromises();
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("Interactive Tool Table renders", async () => {
        const table = wrapper.find("#interactive-tool-table");
        expect(table.exists() === true).toBeTruthy();
    });

    it("Interactive Tool should disappear after stop button pressed", async () => {
        function checkIfExists(tag, toolId) {
            return wrapper.find(tag + toolId).exists();
        }
        const toolId = testInteractiveToolsResponse[0].id;
        const tool = wrapper.vm.activeInteractiveTools.find((tool) => tool.id === toolId);
        expect(checkIfExists("#link-", toolId) === true).toBeTruthy();
        expect(tool.marked === undefined || false).toBeTruthy();

        const checkbox = wrapper.find("#checkbox-" + toolId);
        checkbox.setChecked();
        await flushPromises();
        expect(tool.marked === true).toBeTruthy();

        const stopBtn = wrapper.find("#stopInteractiveTool");
        stopBtn.trigger("click");
        await flushPromises();

        const toolExists = wrapper.vm.activeInteractiveTools.includes((tool) => tool.id === toolId);
        expect(toolExists === false).toBeTruthy();
        expect(checkIfExists("#link-", toolId) === false).toBeTruthy();
    });
});
