import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { disposePinia } from "pinia";
import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { nextTick } from "vue";

import WorkflowInvocationStepHeader from "./WorkflowInvocationStepHeader.vue";

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

describe("WorkflowInvocationStepHeader", () => {
    it("keeps the tool popover a tooltip, since its icon trigger takes no focus", async () => {
        const target = document.createElement("div");
        document.body.appendChild(target);
        onTestFinished(() => target.remove());
        const pinia = createTestingPinia({ createSpy: vi.fn });
        onTestFinished(() => disposePinia(pinia));

        const wrapper = mount(WorkflowInvocationStepHeader, {
            attachTo: target,
            props: {
                workflowStep: {
                    id: 3,
                    type: "tool",
                    tool_id: "cat1",
                    tool_version: "1.0.0",
                    annotation: null,
                    input_steps: {},
                    when: null,
                },
            },
            global: {
                ...withPlugins(localVue, pinia),
                stubs: { ...localVue.stubs, RouterLink: true, WorkflowStepTitle: true },
            },
        });
        await nextTick();
        await nextTick();

        const trigger = wrapper.get("#step-icon-3").element;
        const popover = document.body.querySelector(".popover")!;

        expect(trigger.tagName).toBe("SPAN");
        expect(popover.getAttribute("role")).toBe("tooltip");
        expect(trigger.getAttribute("aria-describedby")).toBe(popover.id);
        // axe flags these on an element without a widget role (aria-allowed-attr, critical).
        expect(trigger.hasAttribute("aria-expanded")).toBe(false);
        expect(trigger.hasAttribute("aria-haspopup")).toBe(false);
        expect(trigger.hasAttribute("aria-controls")).toBe(false);
    });
});
