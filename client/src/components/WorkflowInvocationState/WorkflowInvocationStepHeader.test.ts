import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import WorkflowInvocationStepHeader from "./WorkflowInvocationStepHeader.vue";

const localVue = getLocalVue();

describe("WorkflowInvocationStepHeader", () => {
    it("keeps the tool popover a tooltip, since its icon trigger takes no focus", async () => {
        const wrapper = mount(WorkflowInvocationStepHeader as object, {
            attachTo: document.body,
            props: { workflowStep: { id: 3, type: "tool", tool_id: "cat1", tool_version: "1.0.0" } },
            global: {
                ...withPlugins(localVue, createTestingPinia({ createSpy: vi.fn })),
                stubs: { ...localVue.stubs, RouterLink: true, WorkflowStepTitle: true },
            },
        });
        await nextTick();
        await nextTick();

        const trigger = document.getElementById("step-icon-3")!;
        const popover = document.body.querySelector(".popover")!;

        expect(trigger.tagName).toBe("SPAN");
        expect(popover.getAttribute("role")).toBe("tooltip");
        expect(trigger.getAttribute("aria-describedby")).toBe(popover.id);
        // axe flags these on an element without a widget role (aria-allowed-attr, critical).
        expect(trigger.hasAttribute("aria-expanded")).toBe(false);
        expect(trigger.hasAttribute("aria-haspopup")).toBe(false);
        expect(trigger.hasAttribute("aria-controls")).toBe(false);

        wrapper.unmount();
        document.body.innerHTML = "";
    });
});
