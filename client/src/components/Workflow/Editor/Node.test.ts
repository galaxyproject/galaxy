import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";

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

describe("Node", () => {
    it("test attributes", async () => {
        const testingPinia = createTestingPinia({ createSpy: vi.fn });
        setActivePinia(testingPinia);
        const wrapper = shallowMount(Node as any, {
            propsData: {
                id: 0,
                contentId: "tool name",
                activeNodeId: 0,
                name: "node-name",
                step: { type: "tool", inputs: [], outputs: [], position: { top: 0, left: 0 } },
                datatypesMapper: testDatatypesMapper,
                rootOffset: mockOffset,
                scroll: MOCK_SCROLL,
            },
            localVue,
            pinia: testingPinia,
            provide: {
                workflowId: "mock-workflow",
            },
        });
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
});
