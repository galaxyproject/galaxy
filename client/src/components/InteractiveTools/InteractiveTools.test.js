import { createTestingPinia } from "@pinia/testing";
import { setActivePinia, PiniaVuePlugin } from "pinia";
import InteractiveTools from "./InteractiveTools";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import testInteractiveToolsResponse from "./testData/testInteractiveToolsResponse";

describe("InteractiveTools/InteractiveTools.vue", () => {
    const localVue = getLocalVue();
    localVue.use(PiniaVuePlugin);
    let wrapper;
    let testPinia;

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
    });

    it("renders table with interactive tools", async () => {
        expect(wrapper.get("#interactive-tool-table").exists() === true).toBeTruthy();
        expect(wrapper.findAll("td > a").length).toBe(2);
    });

    it("removes the interactive tool after stop button is pressed", async () => {
        function checkIfExists(tag, toolId) {
            return wrapper.find(tag + toolId).exists();
        }

        const toolId = testInteractiveToolsResponse[0].id;
        const tool = wrapper.vm.activeInteractiveTools.find((tool) => tool.id === toolId);
        expect(checkIfExists("#link-", toolId) === true).toBeTruthy();
        expect(tool.marked === undefined || false).toBeTruthy();

        const checkbox = wrapper.get("#checkbox-" + toolId);
        checkbox.setChecked();
        await new Promise((_) => setTimeout(_, 10));
        expect(tool.marked === true).toBeTruthy();

        const stopBtn = wrapper.get("#stopInteractiveTool");
        stopBtn.trigger("click");
        await new Promise((_) => setTimeout(_, 10));
        wrapper.vm.activeInteractiveTools.splice(0, 1);
        await new Promise((_) => setTimeout(_, 10));

        const deletedTool = wrapper.vm.activeInteractiveTools.filter((tool) => tool.id === toolId);
        expect(deletedTool.length).toBe(0);
        expect(checkIfExists("#link-", toolId) === false).toBeTruthy();
    });
});
