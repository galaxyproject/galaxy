import { createTestingPinia } from "@pinia/testing";
import { composeStories } from "@storybook/vue3-vite";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { zoomIdentity } from "d3-zoom";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { ref } from "vue";

import { getGalaxyInstance, setGalaxyInstance } from "@/app";
import { GalaxyApp } from "@/app/galaxy";
import { useWorkflowNodeInspectorStore } from "@/stores/workflowNodeInspectorStore";

import * as NodeStories from "./Node.stories";
import { SUBWORKFLOW_STEP, TOOL_STEP } from "./node_test_fixtures";

import Node from "./Node.vue";
import NodeInput from "./NodeInput.vue";
import NodeOutput from "./NodeOutput.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

const stories = composeStories(NodeStories);
const mountStory = useStoryMount();
enableAutoUnmount(afterEach);

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

function mountNode(story: StoryOf<typeof stories> = stories.Tool) {
    const mounted = mountStory(story, { pinia: { stubActions: true } });
    return { wrapper: mounted.getComponent(Node), inspectorStore: useWorkflowNodeInspectorStore() };
}

describe("Node", () => {
    it("renders an active tool node, then the subworkflow icon and label after the step changes", async () => {
        // A live prop update must keep the same node instance; composed stories remount on setProps.
        const previous = getGalaxyInstance();
        setGalaxyInstance(new GalaxyApp({ config: { enable_tool_recommendations: false } }));
        const wrapper = mount(Node, {
            props: { ...NodeStories.default.args, ...NodeStories.ActiveTool.args },
            global: {
                ...withPlugins(getLocalVue(), createTestingPinia({ createSpy: vi.fn })),
                provide: { workflowId: "quality-control", transform: ref(zoomIdentity), isDragging: ref(false) },
            },
        });
        onTestFinished(() => {
            (window as { _galaxyInstance?: unknown })._galaxyInstance = previous;
        });
        await flushPromises();

        expect(wrapper.classes()).toContain("is-active");
        expect(wrapper.findAll(SELECTORS.TOOL_ICON)).toHaveLength(1);

        await wrapper.setProps({ step: SUBWORKFLOW_STEP });

        expect(wrapper.findAll(SELECTORS.SUBWORKFLOW_ICON)).toHaveLength(1);
        expect(wrapper.findAll(SELECTORS.TOOL_ICON)).toHaveLength(0);
        expect(wrapper.find(SELECTORS.TITLE).text()).toBe("Read quality control");
    });

    describe("step with errors", () => {
        it("renders terminals for connections of a missing tool", async () => {
            const { wrapper } = mountNode(stories.MissingToolWithConnections);
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
            const { wrapper } = mountNode(stories.MissingTool);
            await flushPromises();

            expect(wrapper.find(SELECTORS.ERROR).classes()).toContain("rounded-bottom");
            expect(wrapper.find(SELECTORS.BODY).exists()).toBe(false);
        });
    });

    it("lets keyboard users into the tool recommendations popover", async () => {
        const { wrapper } = mountNode(stories.WithRecommendations);
        await flushPromises();

        expect(wrapper.findComponent(GPopover).props("interactive")).toBe(true);
    });

    it("keeps Enter on the tool recommendations button from activating the node", async () => {
        const { wrapper } = mountNode(stories.WithRecommendations);
        await flushPromises();

        await wrapper.find(SELECTORS.RECOMMENDATIONS_BUTTON).trigger("keyup.enter");

        expect(wrapper.emitted("onActivate")).toBeUndefined();

        await wrapper.find(SELECTORS.HEADER).trigger("keyup.enter");

        expect(wrapper.emitted("onActivate")).toEqual([[0]]);
    });

    describe("double click", () => {
        async function clickNode(wrapper: ReturnType<typeof mountNode>["wrapper"]) {
            const header = wrapper.find(SELECTORS.HEADER);
            await header.trigger("pointerdown");
            await header.trigger("pointerup");
        }

        it("maximizes the inspector on a native double click", async () => {
            const { wrapper, inspectorStore } = mountNode();
            await flushPromises();

            await clickNode(wrapper);
            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();

            await wrapper.find(SELECTORS.HEADER).trigger("dblclick");

            expect(inspectorStore.setMaximized).toHaveBeenCalledWith(TOOL_STEP, true);
        });

        it("does not maximize the inspector for consecutive pointer clicks", async () => {
            const { wrapper, inspectorStore } = mountNode();
            await flushPromises();

            await clickNode(wrapper);
            await clickNode(wrapper);

            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();
        });

        it("does not maximize the inspector for clicks or double clicks on a node control", async () => {
            const { wrapper, inspectorStore } = mountNode();
            await flushPromises();

            await clickNode(wrapper);
            await wrapper.find(SELECTORS.CLONE_BUTTON).trigger("pointerup");
            await wrapper.find(SELECTORS.CLONE_BUTTON).trigger("dblclick");
            await clickNode(wrapper);

            expect(inspectorStore.setMaximized).not.toHaveBeenCalled();
        });
    });
});
