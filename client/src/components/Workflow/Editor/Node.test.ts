import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, shallowMount } from "@vue/test-utils";
import { zoomIdentity } from "d3-zoom";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useWorkflowNodeInspectorStore } from "@/stores/workflowNodeInspectorStore";

import { mockOffset } from "./test_fixtures";

import Node from "./Node.vue";

vi.mock("@/app", () => ({
    getGalaxyInstance: vi.fn(() => ({
        config: { enable_tool_recommendations: false },
    })),
}));

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
    const testingPinia = createTestingPinia({ createSpy: vi.fn });
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
        async function clickNode(wrapper: ReturnType<typeof mount>) {
            const header = wrapper.find(".card-header");
            await header.trigger("pointerdown");
            await header.trigger("pointerup");
        }

        it("maximizes the inspector on a native double click", async () => {
            const { wrapper, inspectorStore } = mountNode(mount);
            await flushPromises();

            await clickNode(wrapper);
            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();

            await wrapper.find(".card-header").trigger("dblclick");

            expect(inspectorStore.setMaximized).toHaveBeenCalledWith(TOOL_STEP, true);
        });

        it("does not maximize the inspector for consecutive pointer clicks", async () => {
            const { wrapper, inspectorStore } = mountNode(mount);
            await flushPromises();

            await clickNode(wrapper);
            await clickNode(wrapper);

            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();
        });

        it("does not maximize the inspector for clicks or double clicks on a node control", async () => {
            const { wrapper, inspectorStore } = mountNode(mount);
            await flushPromises();

            await clickNode(wrapper);
            await wrapper.find("button.node-clone").trigger("pointerup");
            await wrapper.find("button.node-clone").trigger("dblclick");
            await clickNode(wrapper);

            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();
        });
    });
});
