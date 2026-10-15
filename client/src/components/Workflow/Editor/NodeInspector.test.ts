import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { useWorkflowNodeInspectorStore } from "@/stores/workflowNodeInspectorStore";
import type { Step } from "@/stores/workflowStepStore";

import { simpleSteps } from "./test_fixtures";

import NodeInspector from "./NodeInspector.vue";

const step = Object.values(simpleSteps)[0] as Step;

describe("NodeInspector", () => {
    it("stores the size when remember size is checked", async () => {
        const wrapper = mount(NodeInspector as object, {
            props: { step, datatypes: [] },
            global: {
                plugins: [createTestingPinia({ createSpy: vi.fn })],
                stubs: { FormTool: true, FormDefault: true, IdleLoad: true, DraggableSeparator: true },
            },
        });
        const inspectorStore = useWorkflowNodeInspectorStore();

        await wrapper.find("input[type='checkbox']").setValue(true);

        expect(inspectorStore.setStored).toHaveBeenCalledWith(step, true);
    });
});
