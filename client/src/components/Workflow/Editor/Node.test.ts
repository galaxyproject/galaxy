import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, shallowMount } from "@vue/test-utils";
import { zoomIdentity } from "d3-zoom";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowNodeInspectorStore } from "@/stores/workflowNodeInspectorStore";
import type { Connection } from "@/stores/workflowStoreTypes";

import { mockOffset } from "./test_fixtures";

import Node from "./Node.vue";
import NodeInput from "./NodeInput.vue";
import NodeOutput from "./NodeOutput.vue";

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

const MISSING_TOOL_STEP = {
    ...TOOL_STEP,
    errors: "Tool is not installed",
};

const MISSING_TOOL_CONNECTIONS: Connection[] = [
    {
        input: { stepId: 0, name: "input1", connectorType: "input" },
        output: { stepId: 1, name: "output", connectorType: "output" },
    },
    {
        input: { stepId: 2, name: "input1", connectorType: "input" },
        output: { stepId: 0, name: "out_file1", connectorType: "output" },
    },
];

function mountNode(mounter: typeof shallowMount = shallowMount, propsData = {}, connections: Connection[] = []) {
    const testingPinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(testingPinia);
    useConnectionStore("mock-workflow").$patch({ stepToConnections: { 0: connections } });

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
        global: localVue,
        pinia: testingPinia,
        provide: { workflowId: "mock-workflow", transform: ref(zoomIdentity), isDragging: ref(false) },
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

    describe("step with errors", () => {
        it("renders terminals for connections of a missing tool", async () => {
            const { wrapper } = mountNode(mount, { step: MISSING_TOOL_STEP }, MISSING_TOOL_CONNECTIONS);
            await flushPromises();

            expect(wrapper.find(".node-error").text()).toBe("Tool is not installed");
            expect(wrapper.find(".node-error").classes()).not.toContain("rounded-bottom");
            const inputs = wrapper.findAllComponents(NodeInput);
            expect(inputs).toHaveLength(1);
            expect(inputs.at(0).props("input")).toMatchObject({ name: "input1", valid: false });
            const outputs = wrapper.findAllComponents(NodeOutput);
            expect(outputs).toHaveLength(1);
            expect(outputs.at(0).props("output")).toMatchObject({ name: "out_file1", valid: false });
        });

        it("renders only the error for a missing tool without connections", async () => {
            const { wrapper } = mountNode(mount, { step: MISSING_TOOL_STEP });
            await flushPromises();

            expect(wrapper.find(".node-error").classes()).toContain("rounded-bottom");
            expect(wrapper.find(".node-body").exists()).toBe(false);
        });
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
