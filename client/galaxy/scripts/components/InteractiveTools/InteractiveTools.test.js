import InteractiveTools from "./InteractiveTools";
import { mount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";
import _l from "utils/localization";
import testInteractiveToolsResponse from "./testData/testInteractiveToolsResponse";

import MockAdapter from "axios-mock-adapter";
import axios from "axios";

describe("InteractiveTools/InteractiveTools.vue", () => {
    const localVue = createLocalVue();
    localVue.filter("localize", (value) => _l(value));
    let wrapper;
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
        axiosMock.onGet("/api/entry_points?running=true").reply(200, testInteractiveToolsResponse);
        axiosMock.onPost("/interactivetool/list").reply(200, { status: "ok", message: "ok" });
        await flushPromises();
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("Interactive Tool Table renders", async () => {
        const table = wrapper.find("#workflow-table");
        assert(table.exists() === true, "Interactive Tools table doesn't exist");
    });

    it("Interactive Tool should disappear after stop button pressed", async () => {
        function checkIfExists(tag, toolId) {
            return wrapper.find(tag + toolId).exists();
        }
        const toolId = testInteractiveToolsResponse[0].id;
        const tool = wrapper.vm.activeInteractiveTools.find((tool) => tool.id === toolId);
        assert(checkIfExists("#link-", toolId) === true, "tool is not rendered");
        assert(tool.marked === undefined || false, "tool was selected before click");

        const checkbox = wrapper.find("#checkbox-" + toolId);
        checkbox.setChecked();
        await flushPromises();
        assert(tool.marked === true, "Clicking on checkbox did not select corresponding tool");

        const stopBtn = wrapper.find("#stopInteractiveTool");
        stopBtn.trigger("click");
        await flushPromises();

        const toolExists = wrapper.vm.activeInteractiveTools.includes((tool) => tool.id === toolId);
        assert(toolExists === false, "Interactive Tool was not deleted from the list");
        assert(checkIfExists("#link-", toolId) === false, "Interactive Tool is still rendered after deletion");
    });
});
