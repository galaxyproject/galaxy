import { createTestingPinia } from "@pinia/testing";
import { mount, shallowMount } from "@vue/test-utils";
import { zoomIdentity } from "d3-zoom";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import { ref } from "vue";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useWorkflowNodeInspectorStore } from "@/stores/workflowNodeInspectorStore";

import { mockOffset } from "./test_fixtures";

import Node from "./Node.vue";

jest.mock("app");

const localVue = getLocalVue();

const MOCK_SCROLL = {
    x: { value: 100 },
    y: { value: 200 },
    isScrolling: { value: true },
};

const TOOL_STEP = {
    id: 0,
    type: "tool",
    content_id: "tool_id",
    inputs: [],
    outputs: [],
    position: { top: 0, left: 0 },
};

function mountNode(mounter: typeof shallowMount = shallowMount, propsData = {}) {
    const testingPinia = createTestingPinia();
    setActivePinia(testingPinia);

    const wrapper = mounter(Node as any, {
        propsData: {
            id: 0,
            contentId: "tool_id",
            activeNodeId: null,
            name: "node-name",
            step: TOOL_STEP,
            datatypesMapper: testDatatypesMapper,
            rootOffset: mockOffset,
            scroll: MOCK_SCROLL,
            ...propsData,
        },
        localVue,
        pinia: testingPinia,
        provide: { workflowId: "mock-workflow", transform: ref(zoomIdentity) },
    });

    return { wrapper, inspectorStore: useWorkflowNodeInspectorStore() };
}

describe("Node", () => {
    it("test attributes", async () => {
        const { wrapper } = mountNode(shallowMount, { activeNodeId: 0 });
        await flushPromises();

        // fa-wrench is the tool icon ...
        expect(wrapper.findAll(".fa-wrench")).toHaveLength(1);
        await wrapper.setProps({
            step: { label: "step label", type: "subworkflow", inputs: [], outputs: [], position: { top: 0, left: 0 } },
        });

        // fa-sitemap is the subworkflow icon ...
        expect(wrapper.findAll(".fa-sitemap")).toHaveLength(1);
        expect(wrapper.findAll(".fa-wrench")).toHaveLength(0);

        const workflowTitle = wrapper.find(".node-title");
        expect(workflowTitle.text()).toBe("step label");
    });

    describe("double click", () => {
        let now: number;

        beforeEach(() => {
            now = 1000;
            jest.spyOn(Date, "now").mockImplementation(() => now);
        });
        afterEach(() => jest.restoreAllMocks());

        async function clickNode(wrapper: ReturnType<typeof mount>) {
            const header = wrapper.find(".card-header");
            await header.trigger("pointerdown");
            await header.trigger("pointerup");
        }

        it("maximizes the inspector when the node is clicked twice within the double click timeout", async () => {
            const { wrapper, inspectorStore } = mountNode(mount);
            await flushPromises();

            await clickNode(wrapper);
            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();

            now += 100;
            await clickNode(wrapper);

            expect(inspectorStore.setMaximized).toHaveBeenCalledWith(TOOL_STEP, true);
        });

        it("does not maximize the inspector when the node is clicked twice beyond the double click timeout", async () => {
            const { wrapper, inspectorStore } = mountNode(mount);
            await flushPromises();

            await clickNode(wrapper);
            now += 600;
            await clickNode(wrapper);

            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();
        });

        it("does not maximize the inspector when a button inside the node was clicked in between", async () => {
            const { wrapper, inspectorStore } = mountNode(mount);
            await flushPromises();

            await clickNode(wrapper);
            now += 100;
            await wrapper.find("button.node-clone").trigger("pointerup");
            now += 100;
            await clickNode(wrapper);

            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();
        });
    });
});
