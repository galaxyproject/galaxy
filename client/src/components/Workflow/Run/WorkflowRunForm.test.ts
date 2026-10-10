import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, nth, suppressDebugConsole, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { h, nextTick } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

import { WorkflowRunModel } from "./model";
import { invokeWorkflow } from "./services";
import sampleRunData1 from "./testdata/run1.json";

import WorkflowRunForm from "./WorkflowRunForm.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import FormCard from "@/components/Form/FormCard.vue";

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

const localVue = getLocalVue();

// run1.json has input steps 0 and 4 and tool steps 1-3.
const RUN1_WORKFLOW_ID = "ebab00128497f9d7";
const RUN1_HISTORY_ID = "8f7a155755f10e73";
// The only stored history, so the store falls back to it as the current one.
const CURRENT_HISTORY_ID = "current_history_id";

const SELECTORS = {
    FORM: ".workflow-expanded-form",
    IMMUTABLE_HISTORY_WARNING: ".alert-warning",
};

function mountForm({ canMutateCurrentHistory = true } = {}) {
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        initialState: {
            userStore: { currentUser: { id: "user_id" } },
            historyStore: {
                storedHistories: { [CURRENT_HISTORY_ID]: { id: CURRENT_HISTORY_ID, name: "Current" } },
            },
        },
    });
    return mount(WorkflowRunForm, {
        props: {
            model: new WorkflowRunModel(structuredClone(sampleRunData1)),
            canMutateCurrentHistory,
        },
        global: withPlugins(localVue, pinia),
    });
}

function findStep(wrapper: VueWrapper, index: string) {
    return [
        ...wrapper.findAllComponents({ name: "WorkflowRunDefaultStep" }),
        ...wrapper.findAllComponents({ name: "WorkflowRunInputStep" }),
    ].find((step) => step.props("model").index === index)!;
}

function findCardForm(wrapper: VueWrapper, title: string) {
    const card = wrapper.findAllComponents(FormCard).find((formCard) => formCard.props("title") === title)!;
    return card.findComponent({ name: "FormDisplay" });
}

function clickRun(wrapper: VueWrapper) {
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
        expect(nth(toolSteps, 0).props("historyId")).toBe(CURRENT_HISTORY_ID);
        expect(nth(inputSteps, 0).props("validationScrollTo")).toEqual([]);
    });

    it("stops rendering when the current history goes away", async () => {
        const wrapper = mountForm();
        expect(wrapper.find(SELECTORS.FORM).exists()).toBe(true);

        useHistoryStore().storedHistories = {};
        await nextTick();

        expect(wrapper.find(SELECTORS.FORM).exists()).toBe(false);
    });

    it("asks to switch to the simple form", async () => {
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

        findCardForm(wrapper, "Workflow Parameters").vm.$emit("onChange", { wf_param: "42" });
        await nextTick();

        expect(findStep(wrapper, "3").props("replaceParams")).toEqual({ input: null, "seed_source|seed": "42" });
    });

    it("submits the collected inputs and options", async () => {
        const wrapper = mountForm();
        findStep(wrapper, "0").vm.$emit("onChange", "0", { input: { values: [{ id: "c1", src: "hdca" }] } });
        findStep(wrapper, "4").vm.$emit("onChange", "4", { input: "text" });
        findStep(wrapper, "3").vm.$emit("onChange", "3", { num_lines: "5", input: { values: [] } });
        wrapper.findComponent({ name: "FormElement" }).vm.$emit("input", true);
        wrapper.findComponent({ name: "OnCompleteActions" }).vm.$emit("input", [{ send_notification: {} }]);
        await nextTick();
        expect(wrapper.findComponent({ name: "FormElement" }).props("value")).toBe(true);

        await clickRun(wrapper);

        expect(invokeWorkflow).toHaveBeenCalledWith(RUN1_WORKFLOW_ID, {
            new_history_name: null,
            history_id: RUN1_HISTORY_ID,
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

    it("sends results to a new history when the current one is immutable", async () => {
        const wrapper = mountForm({ canMutateCurrentHistory: false });
        const runButton = wrapper.findComponent({ name: "ButtonSpinner" });
        expect(wrapper.find(SELECTORS.IMMUTABLE_HISTORY_WARNING).exists()).toBe(true);
        expect(runButton.props("disabled")).toBe(true);

        findCardForm(wrapper, "History Options").vm.$emit("onChange", { "new_history|name": "New" });
        await nextTick();
        expect(runButton.props("disabled")).toBe(false);

        await clickRun(wrapper);

        expect(invokeWorkflow).toHaveBeenCalledWith(
            RUN1_WORKFLOW_ID,
            expect.objectContaining({ new_history_name: "New", history_id: null }),
        );
    });

    it("scrolls to the first invalid step instead of submitting", async () => {
        const wrapper = mountForm();
        findStep(wrapper, "0").vm.$emit("onValidation", "0", null);
        findStep(wrapper, "3").vm.$emit("onValidation", "3", ["num_lines", "Required"]);

        await clickRun(wrapper);

        expect(invokeWorkflow).not.toHaveBeenCalled();
        expect(findStep(wrapper, "3").props("validationScrollTo")).toEqual(["num_lines", "Required"]);
        expect(findStep(wrapper, "0").props("validationScrollTo")).toEqual([]);
    });

    it("scrolls to the step named in a server validation error", async () => {
        vi.mocked(invokeWorkflow).mockRejectedValue({
            response: { data: { err_data: { 3: { num_lines: "Invalid value" } } } },
        });
        const wrapper = mountForm();

        await clickRun(wrapper);

        expect(findStep(wrapper, "3").props("validationScrollTo")).toEqual(["num_lines", "Invalid value"]);
        expect(wrapper.emitted("submissionError")).toBeUndefined();
    });

    it("reports other submission errors", async () => {
        const error = new Error("Server unavailable");
        vi.mocked(invokeWorkflow).mockRejectedValue(error);
        const wrapper = mountForm();

        await clickRun(wrapper);

        expect(wrapper.emitted("submissionError")).toEqual([[error]]);
    });
});
