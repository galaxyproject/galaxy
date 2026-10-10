import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { WorkflowInvocationElementView } from "@/api/invocations";

import invocationData from "../Workflow/test/json/invocation.json";

import WorkflowInvocationInputOutputTabs from "./WorkflowInvocationInputOutputTabs.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const SELECTORS = {
    PARAMETERS_TABLE: "[data-description='input table']",
    TERMINAL_OUTPUT: "[data-description='terminal invocation output']",
    TERMINAL_OUTPUT_ITEM: "[data-description='terminal invocation output item']",
    NON_TERMINAL_OUTPUT: "[data-description='non-terminal invocation output']",
    NON_TERMINAL_OUTPUT_LOADING: "[data-description='non-terminal invocation output loading']",
};

const INVOCATION = invocationData as WorkflowInvocationElementView;
const DATA_INPUT = invocationData.inputs["0"];
const PARAMETER_INPUT = invocationData.input_step_parameters["Workflow Input Parameter"];
const DATASET_OUTPUT_LABELS = Object.keys(invocationData.outputs);
const COLLECTION_OUTPUT_LABELS = Object.keys(invocationData.output_collections);
const OUTPUT_LABELS = [...DATASET_OUTPUT_LABELS, ...COLLECTION_OUTPUT_LABELS];

const WORKFLOW = { id: "workflow-id", name: "Test Workflow", version: 0 };

function workflowOutputsStep(labels: string[]) {
    return { workflow_outputs: labels.map((label) => ({ output_name: "output", label, uuid: "uuid" })) };
}

/** The editor-style workflow marking the invocation's dataset and collection outputs as workflow outputs. */
const FULL_WORKFLOW = {
    ...WORKFLOW,
    steps: {
        "0": workflowOutputsStep(DATASET_OUTPUT_LABELS),
        "1": workflowOutputsStep(COLLECTION_OUTPUT_LABELS),
    },
};

/**
 * Mounts the tabs for `invocation`, with `storedWorkflow` already in the workflow store
 * under the invocation's `workflow_id` when given.
 */
async function mountTabs(
    invocation: WorkflowInvocationElementView,
    {
        tab = "inputs",
        terminal = true,
        storedWorkflow,
    }: { tab?: "inputs" | "outputs"; terminal?: boolean; storedWorkflow?: typeof WORKFLOW } = {},
) {
    const workflowsByInstanceId = storedWorkflow ? { [invocation.workflow_id]: storedWorkflow } : {};
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        stubActions: false,
        initialState: { workflowStore: { workflowsByInstanceId } },
    });
    const wrapper = mount(WorkflowInvocationInputOutputTabs, {
        props: { invocation, tab, terminal },
        global: withPlugins(localVue, pinia),
    });
    await flushPromises();
    return wrapper;
}

function expectOutputSections(wrapper: VueWrapper, { terminal }: { terminal: boolean }) {
    const sections = wrapper.findAll(terminal ? SELECTORS.TERMINAL_OUTPUT : SELECTORS.NON_TERMINAL_OUTPUT);
    expect(sections).toHaveLength(OUTPUT_LABELS.length);
    OUTPUT_LABELS.forEach((label, index) => {
        const section = nth(sections, index);
        expect(section.text()).toContain(label);
        expect(section.find(SELECTORS.TERMINAL_OUTPUT_ITEM).exists()).toBe(terminal);
        expect(section.find(SELECTORS.NON_TERMINAL_OUTPUT_LOADING).exists()).toBe(!terminal);
    });
}

describe("WorkflowInvocationInputOutputTabs", () => {
    it("lists the data inputs and parameters in the inputs table", async () => {
        const wrapper = await mountTabs(INVOCATION);

        const table = wrapper.find(SELECTORS.PARAMETERS_TABLE);
        expect(table.exists()).toBe(true);
        const rows = table.findAll("tbody tr");
        expect(rows.map((row) => nth(row.findAll("td"), 0).text())).toEqual([DATA_INPUT.label, PARAMETER_INPUT.label]);
        expect(nth(rows, 0).find(`[data-label='${DATA_INPUT.label}']`).exists()).toBe(true);
        expect(nth(nth(rows, 1).findAll("td"), 1).text()).toBe(String(PARAMETER_INPUT.parameter_value));
    });

    it("shows each invocation output with its history item when the invocation is terminal", async () => {
        const wrapper = await mountTabs(INVOCATION, { tab: "outputs" });

        expectOutputSections(wrapper, { terminal: true });
    });

    it("shows the workflow output labels as not created yet when the invocation is not terminal", async () => {
        server.use(http.untyped.get(`/api/workflows/${WORKFLOW.id}/download`, () => HttpResponse.json(FULL_WORKFLOW)));
        const invocationWithoutOutputs = { ...INVOCATION, outputs: {}, output_collections: {} };

        const wrapper = await mountTabs(invocationWithoutOutputs, {
            tab: "outputs",
            terminal: false,
            storedWorkflow: WORKFLOW,
        });

        expectOutputSections(wrapper, { terminal: false });
    });
});
