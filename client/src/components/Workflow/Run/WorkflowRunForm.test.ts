import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, nth, suppressDebugConsole } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { h } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

import { WorkflowRunModel } from "./model";
import { invokeWorkflow } from "./services";
import sampleRunData1 from "./testdata/run1.json";

import WorkflowRunForm from "./WorkflowRunForm.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

vi.mock("./services", () => ({
    invokeWorkflow: vi.fn(),
}));

function stub(name: string, props: string[]) {
    return { default: { name, props, render: () => h("div") } };
}

vi.mock("./WorkflowRunDefaultStep.vue", () =>
    stub("WorkflowRunDefaultStep", ["model", "replaceParams", "validationScrollTo", "historyId"]),
);
vi.mock("./WorkflowRunInputStep.vue", () => stub("WorkflowRunInputStep", ["model", "validationScrollTo", "historyId"]));
vi.mock("@/components/Form/FormDisplay.vue", () => stub("FormDisplay", ["inputs"]));
vi.mock("@/components/Form/FormElement.vue", () => stub("FormElement", ["value"]));
vi.mock("@/components/Common/ButtonSpinner.vue", () => stub("ButtonSpinner", ["disabled", "wait", "tooltip"]));
vi.mock("@/components/Workflow/Run/OnCompleteActions.vue", () => stub("OnCompleteActions", ["value"]));
vi.mock("@/components/Workflow/Run/WorkflowCredentials.vue", () => stub("WorkflowCredentials", ["toolIdentifiers"]));

const globalConfig = getLocalVue();

const HISTORY_ID = "8f7a155755f10e73";

function mountForm(canMutateCurrentHistory = true) {
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        initialState: {
            userStore: { currentUser: { id: "user_id" } },
            historyStore: {
                storedHistories: { current_history_id: { id: "current_history_id", name: "Current" } },
            },
        },
    });
    setActivePinia(pinia);
    return mount(WorkflowRunForm as object, {
        props: {
            model: new WorkflowRunModel(JSON.parse(JSON.stringify(sampleRunData1))),
            canMutateCurrentHistory,
        },
        global: {
            ...globalConfig,
            plugins: [...(globalConfig.plugins ?? []), pinia],
        },
    });
}

function findStep(wrapper: VueWrapper, index: string) {
    return [
        ...wrapper.findAllComponents({ name: "WorkflowRunDefaultStep" }),
        ...wrapper.findAllComponents({ name: "WorkflowRunInputStep" }),
    ].find((step) => step.props("model").index === index)!;
}

function run(wrapper: VueWrapper) {
    wrapper.findComponent({ name: "ButtonSpinner" }).vm.$emit("onClick");
    return flushPromises();
}

describe("WorkflowRunForm", () => {
    beforeEach(() => {
        suppressDebugConsole();
        vi.mocked(invokeWorkflow).mockReset();
        vi.mocked(invokeWorkflow).mockResolvedValue([{ id: "invocation_id" }]);
    });

    it("renders a form per workflow step", () => {
        const wrapper = mountForm();
        const toolSteps = wrapper.findAllComponents({ name: "WorkflowRunDefaultStep" });
        const inputSteps = wrapper.findAllComponents({ name: "WorkflowRunInputStep" });
        expect(toolSteps.map((step) => step.props("model").index)).toEqual(["1", "2", "3"]);
        expect(inputSteps.map((step) => step.props("model").index)).toEqual(["0", "4"]);
        expect(nth(toolSteps, 0).props("historyId")).toBe("current_history_id");
        expect(nth(inputSteps, 0).props("validationScrollTo")).toEqual([]);
    });

    it("renders nothing without a current history", async () => {
        const wrapper = mountForm();
        useHistoryStore().storedHistories = {};
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".workflow-expanded-form").exists()).toBe(false);
    });

    it("switches to the simple form", async () => {
        const wrapper = mountForm();
        await wrapper.findComponent(GButton).trigger("click");
        expect(wrapper.emitted("showSimple")).toHaveLength(1);
    });

    it("replaces workflow parameters in linked step inputs", async () => {
        const wrapper = mountForm();
        expect(findStep(wrapper, "3").props("replaceParams")).toEqual({
            input: null,
            "seed_source|seed": "${wf_param}",
        });
        nth(wrapper.findAllComponents({ name: "FormDisplay" }), 0).vm.$emit("onChange", { wf_param: "42" });
        await wrapper.vm.$nextTick();
        expect(findStep(wrapper, "3").props("replaceParams")).toEqual({ input: null, "seed_source|seed": "42" });
    });

    it("submits the collected inputs and options", async () => {
        const wrapper = mountForm();
        findStep(wrapper, "0").vm.$emit("onChange", "0", { input: { values: [{ id: "c1", src: "hdca" }] } });
        findStep(wrapper, "4").vm.$emit("onChange", "4", { input: "text" });
        findStep(wrapper, "3").vm.$emit("onChange", "3", { num_lines: "5", input: { values: [] } });
        wrapper.findComponent({ name: "FormElement" }).vm.$emit("input", true);
        wrapper.findComponent({ name: "OnCompleteActions" }).vm.$emit("input", [{ send_notification: {} }]);
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent({ name: "FormElement" }).props("value")).toBe(true);
        await run(wrapper);
        expect(invokeWorkflow).toHaveBeenCalledWith("ebab00128497f9d7", {
            new_history_name: null,
            history_id: HISTORY_ID,
            resource_params: undefined,
            replacement_params: {},
            use_cached_job: true,
            inputs: { 0: { values: [{ id: "c1", src: "hdca" }] }, 4: "text" },
            parameters: { 3: { num_lines: "5" } },
            parameters_normalized: true,
            batch: true,
            require_exact_tool_versions: false,
            version: 9,
            on_complete: [{ send_notification: {} }],
        });
        expect(wrapper.emitted("submissionSuccess")).toEqual([[[{ id: "invocation_id" }]]]);
    });

    it("sends results to a new history when requested", async () => {
        const wrapper = mountForm(false);
        const button = wrapper.findComponent({ name: "ButtonSpinner" });
        expect(wrapper.find(".alert-warning").exists()).toBe(true);
        expect(button.props("disabled")).toBe(true);
        nth(wrapper.findAllComponents({ name: "FormDisplay" }), 1).vm.$emit("onChange", { "new_history|name": "New" });
        await wrapper.vm.$nextTick();
        expect(button.props("disabled")).toBe(false);
        await run(wrapper);
        expect(invokeWorkflow).toHaveBeenCalledWith(
            "ebab00128497f9d7",
            expect.objectContaining({ new_history_name: "New", history_id: null }),
        );
    });

    it("scrolls to the first invalid step instead of submitting", async () => {
        const wrapper = mountForm();
        findStep(wrapper, "0").vm.$emit("onValidation", "0", null);
        findStep(wrapper, "3").vm.$emit("onValidation", "3", ["num_lines", "Required"]);
        await run(wrapper);
        expect(invokeWorkflow).not.toHaveBeenCalled();
        expect(findStep(wrapper, "3").props("validationScrollTo")).toEqual(["num_lines", "Required"]);
        expect(findStep(wrapper, "0").props("validationScrollTo")).toEqual([]);
    });

    it("scrolls to the step named in a server validation error", async () => {
        vi.mocked(invokeWorkflow).mockRejectedValue({
            response: { data: { err_data: { 3: { num_lines: "Invalid value" } } } },
        });
        const wrapper = mountForm();
        await run(wrapper);
        expect(findStep(wrapper, "3").props("validationScrollTo")).toEqual(["num_lines", "Invalid value"]);
        expect(wrapper.emitted("submissionError")).toBeUndefined();
    });

    it("reports other submission errors", async () => {
        const error = new Error("Server unavailable");
        vi.mocked(invokeWorkflow).mockRejectedValue(error);
        const wrapper = mountForm();
        await run(wrapper);
        expect(wrapper.emitted("submissionError")).toEqual([[error]]);
    });
});
