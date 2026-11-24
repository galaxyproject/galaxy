import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";

import { simpleSteps } from "./test_fixtures";

import NodeInspector from "./NodeInspector.vue";

const localVue = getLocalVue();

const step = Object.values(simpleSteps)[0] as Step;

function mountInspector(inspectedStep: Step, stepLoadingState = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    useWorkflowStateStore("mock-workflow").stepLoadingState = stepLoadingState;
    return mount(NodeInspector as object, {
        props: { step: inspectedStep, datatypes: [] },
        global: {
            ...withPlugins(localVue, pinia),
            provide: { workflowId: "mock-workflow" },
            stubs: {
                FormTool: true,
                FormDefault: true,
                MissingToolForm: true,
                IdleLoad: { template: "<div><slot /></div>" },
                DraggableSeparator: true,
            },
        },
    });
}

describe("NodeInspector", () => {
    it("shows the tool form for an installed tool", () => {
        const wrapper = mountInspector({
            ...step,
            type: "tool",
            content_id: "cat1",
            config_form: { id: "cat1", inputs: [] },
        });
        expect(wrapper.findComponent({ name: "FormTool" }).exists()).toBe(true);
        expect(wrapper.findComponent({ name: "MissingToolForm" }).exists()).toBe(false);
    });

    const missingToolStep: Step = {
        ...step,
        type: "tool",
        content_id: "missing_tool",
        config_form: null as unknown as undefined,
        errors: "Tool is not installed" as unknown as string[],
    };

    it("shows the missing tool form when the tool has no config form", () => {
        const wrapper = mountInspector(missingToolStep);
        const form = wrapper.findComponent({ name: "MissingToolForm" });
        expect(form.exists()).toBe(true);
        expect(form.props("error")).toBe("Tool is not installed");
        expect(wrapper.findComponent({ name: "FormTool" }).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "FormDefault" }).exists()).toBe(false);
    });

    const insertedToolStep: Step = { ...step, type: "tool", content_id: "cat1", config_form: undefined, errors: null };

    it("shows a loading message while the tool step is loading", () => {
        const wrapper = mountInspector(insertedToolStep, { [step.id]: { loading: true } });
        expect(wrapper.find("[data-description='loading message']").text()).toContain("Loading tool");
        expect(wrapper.findComponent({ name: "MissingToolForm" }).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "FormDefault" }).exists()).toBe(false);
    });

    it("shows the missing tool form with the error from a failed tool step load", () => {
        const wrapper = mountInspector(insertedToolStep, {
            [step.id]: { loading: false, error: "Tool cat1 not found" },
        });
        expect(wrapper.findComponent({ name: "MissingToolForm" }).props("error")).toBe("Tool cat1 not found");
    });

    it("re-emits label, annotation and step edits from the missing tool form", () => {
        const wrapper = mountInspector(missingToolStep);
        const form = wrapper.findComponent({ name: "MissingToolForm" });

        form.vm.$emit("onLabel", 3, "x");
        form.vm.$emit("onAnnotation", 3, "notes");
        form.vm.$emit("onUpdateStep", 3, { when: "$(inputs.when)" });

        expect(wrapper.emitted("labelChanged")).toEqual([["3", "x"]]);
        expect(wrapper.emitted("annotationChanged")).toEqual([["3", "notes"]]);
        expect(wrapper.emitted("stepUpdated")).toEqual([[3, { when: "$(inputs.when)" }]]);
    });

    it("shows the default form for non-tool steps", () => {
        const wrapper = mountInspector({ ...step, type: "data_input", config_form: { inputs: [] } });
        expect(wrapper.findComponent({ name: "FormDefault" }).exists()).toBe(true);
        expect(wrapper.findComponent({ name: "MissingToolForm" }).exists()).toBe(false);
    });
});
