import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, shallowMount } from "@vue/test-utils";
import type { UseScrollReturn } from "@vueuse/core";
import { zoomIdentity } from "d3-zoom";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowNodeInspectorStore } from "@/stores/workflowNodeInspectorStore";
import type { Step } from "@/stores/workflowStepStore";
import type { Connection } from "@/stores/workflowStoreTypes";

import { mockOffset } from "./test_fixtures";

import Node from "./Node.vue";
import NodeInput from "./NodeInput.vue";
import NodeOutput from "./NodeOutput.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

const galaxyConfig = vi.hoisted(() => ({ enable_tool_recommendations: false }));

vi.mock("@/app", () => ({
    getGalaxyInstance: vi.fn(() => ({
        config: galaxyConfig,
    })),
}));

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

const WORKFLOW_ID = "mock-workflow";

const SELECTORS = {
    HEADER: ".card-header",
    TITLE: ".node-title",
    TOOL_ICON: ".fa-wrench",
    SUBWORKFLOW_ICON: ".fa-sitemap",
    ERROR: ".node-error",
    BODY: ".node-body",
    CLONE_BUTTON: "button.node-clone",
    RECOMMENDATIONS_BUTTON: "button.node-recommendations",
};

const MOCK_SCROLL = {
    x: { value: 100 },
    y: { value: 200 },
    isScrolling: { value: true },
} as UseScrollReturn;

const TOOL_STEP: Step = {
    id: 0,
    name: "tool_id",
    type: "tool",
    content_id: "tool_id",
    input_connections: {},
    tool_state: {},
    inputs: [],
    outputs: [],
    position: { top: 0, left: 0 },
};

const SUBWORKFLOW_STEP: Step = {
    id: 0,
    name: "subworkflow",
    label: "step label",
    type: "subworkflow",
    input_connections: {},
    tool_state: {},
    inputs: [],
    outputs: [],
    position: { top: 0, left: 0 },
};

// The server sends a missing tool's errors as a string, though `Step` types them as `string[]`.
const MISSING_TOOL_STEP = {
    ...TOOL_STEP,
    errors: "Tool is not installed",
} as unknown as Step;

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

interface MountNodeOptions {
    mounter?: typeof shallowMount;
    props?: Record<string, unknown>;
    connections?: Connection[];
    toolRecommendations?: boolean;
}

function mountNode({
    mounter = shallowMount,
    props = {},
    connections = [],
    toolRecommendations = false,
}: MountNodeOptions = {}) {
    // Node reads this once at setup, so it has to be set before mounting.
    galaxyConfig.enable_tool_recommendations = toolRecommendations;
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    useConnectionStore(WORKFLOW_ID).$patch({ stepToConnections: { 0: connections } });

    const wrapper = mounter(Node, {
        props: {
            id: 0,
            contentId: "tool_id",
            activeNodeId: null,
            name: "node-name",
            step: TOOL_STEP,
            datatypesMapper: testDatatypesMapper,
            rootOffset: mockOffset,
            scroll: MOCK_SCROLL,
            ...props,
        },
        global: {
            ...withPlugins(localVue, pinia),
            provide: { workflowId: WORKFLOW_ID, transform: ref(zoomIdentity), isDragging: ref(false) },
        },
    });

    return { wrapper, inspectorStore: useWorkflowNodeInspectorStore() };
}

describe("Node", () => {
    it("renders an active tool node, then the subworkflow icon and label after the step changes", async () => {
        const { wrapper } = mountNode({ props: { activeNodeId: 0 } });
        await flushPromises();

        expect(wrapper.classes()).toContain("is-active");
        expect(wrapper.findAll(SELECTORS.TOOL_ICON)).toHaveLength(1);

        await wrapper.setProps({ step: SUBWORKFLOW_STEP });

        expect(wrapper.findAll(SELECTORS.SUBWORKFLOW_ICON)).toHaveLength(1);
        expect(wrapper.findAll(SELECTORS.TOOL_ICON)).toHaveLength(0);
        expect(wrapper.find(SELECTORS.TITLE).text()).toBe("step label");
    });

    describe("step with errors", () => {
        it("renders terminals for connections of a missing tool", async () => {
            const { wrapper } = mountNode({
                mounter: mount,
                props: { step: MISSING_TOOL_STEP },
                connections: MISSING_TOOL_CONNECTIONS,
            });
            await flushPromises();

            expect(wrapper.find(SELECTORS.ERROR).text()).toBe("Tool is not installed");
            expect(wrapper.find(SELECTORS.ERROR).classes()).not.toContain("rounded-bottom");
            const inputs = wrapper.findAllComponents(NodeInput);
            expect(inputs).toHaveLength(1);
            expect(nth(inputs, 0).props("input")).toMatchObject({ name: "input1", valid: false });
            const outputs = wrapper.findAllComponents(NodeOutput);
            expect(outputs).toHaveLength(1);
            expect(nth(outputs, 0).props("output")).toMatchObject({ name: "out_file1", valid: false });
        });

        it("renders only the error for a missing tool without connections", async () => {
            const { wrapper } = mountNode({ mounter: mount, props: { step: MISSING_TOOL_STEP } });
            await flushPromises();

            expect(wrapper.find(SELECTORS.ERROR).classes()).toContain("rounded-bottom");
            expect(wrapper.find(SELECTORS.BODY).exists()).toBe(false);
        });
    });

    it("lets keyboard users into the tool recommendations popover", async () => {
        const { wrapper } = mountNode({ toolRecommendations: true });
        await flushPromises();

        expect(wrapper.findComponent(GPopover).props("interactive")).toBe(true);
    });

    it("keeps Enter on the tool recommendations button from activating the node", async () => {
        const { wrapper } = mountNode({ mounter: mount, toolRecommendations: true });
        await flushPromises();

        await wrapper.find(SELECTORS.RECOMMENDATIONS_BUTTON).trigger("keyup.enter");

        expect(wrapper.emitted("onActivate")).toBeUndefined();

        await wrapper.find(SELECTORS.HEADER).trigger("keyup.enter");

        expect(wrapper.emitted("onActivate")).toEqual([[0]]);
    });

    describe("double click", () => {
        async function clickNode(wrapper: ReturnType<typeof mount>) {
            const header = wrapper.find(SELECTORS.HEADER);
            await header.trigger("pointerdown");
            await header.trigger("pointerup");
        }

        it("maximizes the inspector on a native double click", async () => {
            const { wrapper, inspectorStore } = mountNode({ mounter: mount });
            await flushPromises();

            await clickNode(wrapper);
            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();

            await wrapper.find(SELECTORS.HEADER).trigger("dblclick");

            expect(inspectorStore.setMaximized).toHaveBeenCalledWith(TOOL_STEP, true);
        });

        it("does not maximize the inspector for consecutive pointer clicks", async () => {
            const { wrapper, inspectorStore } = mountNode({ mounter: mount });
            await flushPromises();

            await clickNode(wrapper);
            await clickNode(wrapper);

            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();
        });

        it("does not maximize the inspector for clicks or double clicks on a node control", async () => {
            const { wrapper, inspectorStore } = mountNode({ mounter: mount });
            await flushPromises();

            await clickNode(wrapper);
            await wrapper.find(SELECTORS.CLONE_BUTTON).trigger("pointerup");
            await wrapper.find(SELECTORS.CLONE_BUTTON).trigger("dblclick");
            await clickNode(wrapper);

            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();
        });
    });
});
