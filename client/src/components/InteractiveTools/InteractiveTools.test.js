import { createTestingPinia } from "@pinia/testing";
import { setActivePinia, PiniaVuePlugin } from "pinia";
import InteractiveTools from "./InteractiveTools";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import testInteractiveToolsResponse from "./testData/testInteractiveToolsResponse";
import { useEntryPointStore } from "stores/entryPointStore";

import flushPromises from "flush-promises";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";

describe("InteractiveTools/InteractiveTools.vue", () => {
    const localVue = getLocalVue();
    localVue.use(PiniaVuePlugin);
    let wrapper;
    let testPinia;
    let axiosMock;

    beforeEach(async () => {
        testPinia = createTestingPinia({
            initialState: {
                entryPointStore: {
                    entryPoints: testInteractiveToolsResponse,
                },
            },
        });
        setActivePinia(testPinia);
        wrapper = mount(InteractiveTools, {
            localVue,
            pinia: testPinia,
        });
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("renders table with interactive tools", async () => {
        expect(wrapper.get("#interactive-tool-table").exists() === true).toBeTruthy();
        expect(wrapper.findAll("td > a").length).toBe(2);
    });

    it("removes the interactive tool when it is gone from store", async () => {
        function checkIfExists(tag, toolId) {
            return wrapper.find(tag + toolId).exists();
        }
        const toolId = testInteractiveToolsResponse[0].id;
        const tool = wrapper.vm.activeInteractiveTools.find((tool) => tool.id === toolId);
        expect(checkIfExists("#link-", toolId) === true).toBeTruthy();
        expect(tool.marked === undefined || false).toBeTruthy();
        const checkbox = wrapper.get("#checkbox-" + toolId);
        await checkbox.setChecked();
        expect(tool.marked === true).toBeTruthy();

        // drop the tested tool from store
        const store = useEntryPointStore();
        await store.entryPoints.splice(0, 1);

        const deletedTool = wrapper.vm.activeInteractiveTools.filter((tool) => tool.id === toolId);
        expect(deletedTool.length).toBe(0);
        expect(checkIfExists("#link-", toolId) === false).toBeTruthy();
    });

    it("sends a delete request after the stop button is pressed", async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onDelete(new RegExp("/api/entry_points/*")).reply(200, { status: "ok", message: "ok" });
        await wrapper.get("#checkbox-" + testInteractiveToolsResponse[0].id).setChecked();
        await wrapper.get("#stopInteractiveTool").trigger("click");
        expect(axiosMock.history.delete.length).toBe(1);
        expect(axiosMock.history.delete[0].url === "/api/entry_points/b887d74393f85b6d").toBeTruthy();
    });

    it("shows an error message if the tool deletion fails", async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onDelete(new RegExp("/api/entry_points/*")).networkError();
        wrapper.get("#stopInteractiveTool").trigger("click");
        await flushPromises();
        expect(wrapper.get(".alert-danger").text()).toMatch(/Network Error/);
    });
});
