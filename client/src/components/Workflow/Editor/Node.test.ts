import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import Node from "./Node.vue";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { createTestingPinia } from "@pinia/testing";
import type { UseElementBoundingReturn } from "@vueuse/core";
import { toRefs, reactive } from "vue";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";

jest.mock("app");

const _mockOffset = toRefs(reactive({ top: 0, left: 0, bottom: 10, right: 10, width: 100, height: 100, x: 0, y: 0 }));
const mockOffset: UseElementBoundingReturn = { ..._mockOffset, update: () => {} };

const localVue = getLocalVue();

describe("Node", () => {
    it("test attributes", async () => {
        const testingPinia = createTestingPinia();
        setActivePinia(testingPinia);
        const wrapper = shallowMount(Node, {
            propsData: {
                id: 0,
                contentId: "tool name",
                activeNodeId: 0,
                name: "node-name",
                step: { type: "tool", inputs: [], outputs: [], position: { top: 0, left: 0 } },
                datatypesMapper: testDatatypesMapper,
                rootOffset: mockOffset,
            },
            localVue,
            pinia: testingPinia,
        });
        await flushPromises();
        // fa-wrench is the tool icon ...
        expect(wrapper.findAll(".fa-wrench")).toHaveLength(1);
        const toolLinks = wrapper.findAll("i");
        expect(toolLinks.length).toBe(3);
        await wrapper.setProps({
            step: { label: "step label", type: "subworkflow", inputs: [], outputs: [], position: { top: 0, left: 0 } },
        });
        // fa-sitemap is the subworkflow icon ...
        expect(wrapper.findAll(".fa-sitemap")).toHaveLength(1);
        expect(wrapper.findAll(".fa-wrench")).toHaveLength(0);
        const subworkflowLinks = wrapper.findAll("i");
        expect(subworkflowLinks.length).toBe(2);
        const workflowTitle = wrapper.find(".node-title");
        expect(workflowTitle.text()).toBe("step label");
    });
});
