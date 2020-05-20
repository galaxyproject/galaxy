import InteractiveTools from "./InteractiveTools";
import { mount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";
import _l from "utils/localization";
import Vue from "vue";
import testInteractiveToolsResponse from "./testData/testInteractiveToolsResponse";

import MockAdapter from "axios-mock-adapter";
import axios from "axios";

describe("ToolsView/ToolsView.vue", () => {
    const localVue = createLocalVue();
    localVue.filter("localize", (value) => _l(value));
    let wrapper;
    let emitted;
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        wrapper = mount(InteractiveTools, {
            computed: {
                currentHistory() {
                    return {
                        loadCurrentHistory() {},
                    };
                },
            },
        });
        emitted = wrapper.emitted();
        axiosMock.onGet("/api/entry_points?running=true").reply(200, testInteractiveToolsResponse);
        axiosMock.onPost("/interactivetool/list").reply(200, { status: "ok", message: "ok" });
        await flushPromises();
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("table should exist", async () => {
        const table = wrapper.find("#workflow-table");
        assert(table.exists() === true, "Interactive Tools table doesn't exist!");
    });

    it("selected tool should disappear after stop button pressed", async () => {
        function checkIfExists(tag, toolId) {
            return wrapper.find(tag + toolId).exists();
        }
        const toolId = testInteractiveToolsResponse[0].id;
        const tool = wrapper.vm.activeInteractiveTools.find((tool) => tool.id === toolId);

        assert(checkIfExists("#link-", toolId) === true, "tool is not rendered!");
        // ensure that the tool is not marked
        assert(tool.marked === undefined || false, "tool was marked before click!");
        // mark & delete tool
        const checkbox = wrapper.find("#checkbox-" + toolId);
        checkbox.trigger("click");
        await flushPromises();
        // ensure that the tool is marked
        assert(tool.marked === true, "clicking on checkbox did not mark corresponding tool!");

        const stopBtn = wrapper.find("#stopInteractiveTool");
        stopBtn.trigger("click");

        await flushPromises();

        const toolExists = wrapper.vm.activeInteractiveTools.includes((tool) => tool.id === toolId);
        // ensure that the tool was deleted from the list
        assert(toolExists === false, "tool was not deleted from the list!");
        assert(checkIfExists("#link-", toolId) === false, "tool is rendered after deletion!");
    });
});
