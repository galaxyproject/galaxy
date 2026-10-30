import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { type Step, useWorkflowStepStore } from "@/stores/workflowStepStore";

import FormConditional from "./FormConditional.vue";
import MissingToolForm from "./MissingToolForm.vue";

const localVue = getLocalVue();

const TOOL_ID = "toolshed.g2.bx.psu.edu/repos/iuc/missing_tool/missing_tool/1.0.0";

function makeStep(overrides: Partial<Step> = {}): Step {
    return {
        id: 3,
        type: "tool",
        name: TOOL_ID,
        content_id: TOOL_ID,
        label: "my label",
        annotation: "my annotation",
        config_form: undefined,
        errors: ["Tool is not installed"],
        input_connections: {},
        inputs: [],
        outputs: [],
        tool_state: {},
        post_job_actions: {},
        ...overrides,
    };
}

function mountTarget(step: Step = makeStep(), workflowOutputLabels: string[] = []) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    if (workflowOutputLabels.length) {
        useWorkflowStepStore("mock-workflow").steps = {
            "1": makeStep({
                id: 1,
                label: "other step",
                workflow_outputs: workflowOutputLabels.map((label) => ({ label, output_name: "out_file1" })),
            }),
        };
    }
    return mount(MissingToolForm as object, {
        props: { step },
        global: { ...withPlugins(localVue, pinia), provide: { workflowId: "mock-workflow" } },
    });
}

describe("MissingToolForm", () => {
    it("explains that the tool is not installed and names it", () => {
        const wrapper = mountTarget();
        const alert = wrapper.find("[data-description='missing tool alert']");
        expect(alert.exists()).toBe(true);
        expect(alert.classes()).toContain("alert-warning");
        expect(alert.text()).toContain("Tool is not installed");
        expect(alert.text()).toContain(TOOL_ID);
        expect(alert.text()).toContain("Version: 1.0.0");
        expect(wrapper.find(".portlet-title-text").text()).toBe("missing_tool");
    });

    it("prefers the step's tool version", () => {
        const wrapper = mountTarget(makeStep({ tool_version: "2.0" }));
        expect(wrapper.find("[data-description='missing tool alert']").text()).toContain("Version: 2.0");
    });

    it("names local tools by their id and omits an unknown version", () => {
        const wrapper = mountTarget(makeStep({ content_id: "cat_missing", name: "cat_missing" }));
        expect(wrapper.find(".portlet-title-text").text()).toBe("cat_missing");
        expect(wrapper.find("[data-description='missing tool alert']").text()).not.toContain("Version");
    });

    it("emits label and annotation edits", async () => {
        const wrapper = mountTarget();

        const label = wrapper.find("input#__label");
        expect((label.element as HTMLInputElement).value).toBe("my label");
        await label.setValue("new label");
        expect(nth(wrapper.emitted("onLabel"), -1)).toEqual([3, "new label"]);

        const annotation = wrapper.find("textarea#__annotation");
        expect((annotation.element as HTMLTextAreaElement).value).toBe("my annotation");
        await annotation.setValue("new annotation");
        expect(nth(wrapper.emitted("onAnnotation"), -1)).toEqual([3, "new annotation"]);
    });

    it("flags a label that is already used as a workflow output label", () => {
        const wrapper = mountTarget(makeStep(), ["my label"]);
        expect(wrapper.text()).toContain("Duplicate label my label. Please fix this before saving the workflow.");
    });

    it("does not flag a unique label", () => {
        const wrapper = mountTarget(makeStep(), ["another label"]);
        expect(wrapper.text()).not.toContain("Duplicate label");
    });

    it("forwards conditional step updates", () => {
        const wrapper = mountTarget();
        const conditional = wrapper.findComponent(FormConditional);
        expect(conditional.exists()).toBe(true);
        conditional.vm.$emit("onUpdateStep", 3, { when: undefined });
        expect(nth(wrapper.emitted("onUpdateStep"), 0)).toEqual([3, { when: undefined }]);
    });
});
