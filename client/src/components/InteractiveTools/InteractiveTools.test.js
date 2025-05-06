import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { PiniaVuePlugin, setActivePinia } from "pinia";
import { useEntryPointStore } from "stores/entryPointStore";
import { getLocalVue } from "tests/jest/helpers";

import InteractiveTools from "./InteractiveTools";
import testInteractiveToolsResponse from "./testData/testInteractiveToolsResponse";

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
        expect(wrapper.get("#interactive-tool-table").exists()).toBeTruthy();
        // Each entry has 2 links: one to open inline and one to open in new tab
        expect(wrapper.findAll("td > a").length).toBe(4);
    });

    it("displays interactive tool information correctly", async () => {
        const firstTool = testInteractiveToolsResponse[0];
        const toolName = wrapper.find(`#link-${firstTool.id}`);
        expect(toolName.text()).toContain(firstTool.name);

        // Check if the external link is present
        const externalLink = wrapper.find(`#external-link-${firstTool.id}`);
        expect(externalLink.exists()).toBeTruthy();
        expect(externalLink.attributes("href")).toBe(firstTool.target);
        expect(externalLink.attributes("target")).toBe("_blank");
    });

    it("removes the interactive tool when it is gone from store", async () => {
        function checkIfExists(tag, toolId) {
            return wrapper.find(tag + toolId).exists();
        }
        const toolId = testInteractiveToolsResponse[0].id;
        expect(checkIfExists("#link-", toolId)).toBeTruthy();

        // drop the tested tool from store
        const store = useEntryPointStore();
        await store.entryPoints.splice(0, 1);

        expect(checkIfExists("#link-", toolId)).toBeFalsy();
    });

    it("sends a delete request after the stop button is pressed", async () => {
        axiosMock.onDelete(new RegExp("/api/entry_points/*")).reply(200, { status: "ok", message: "ok" });
        await wrapper.get(`#stop-${testInteractiveToolsResponse[0].id}`).trigger("click");
        expect(axiosMock.history.delete.length).toBe(1);
        expect(
            axiosMock.history.delete[0].url === `/api/entry_points/${testInteractiveToolsResponse[0].id}`
        ).toBeTruthy();
    });

    it("shows an error message if the tool deletion fails", async () => {
        axiosMock.onDelete(new RegExp("/api/entry_points/*")).networkError();
        await wrapper.get(`#stop-${testInteractiveToolsResponse[0].id}`).trigger("click");
        await flushPromises();
        expect(wrapper.get(".alert-danger").text()).toMatch(/Network Error/);
    });
});
