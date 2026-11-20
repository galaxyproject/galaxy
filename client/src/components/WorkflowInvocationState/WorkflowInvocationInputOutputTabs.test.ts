import { createTestingPinia } from "@pinia/testing";
import { nth } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { WorkflowInvocationElementView } from "@/api/invocations";
import { type InvocationSelection, useInvocationSelection } from "@/composables/invocationSelection";

import invocationData from "../Workflow/test/json/invocation.json";

import WorkflowInvocationInputOutputTabs from "./WorkflowInvocationInputOutputTabs.vue";
import GenericItem from "@/components/History/Content/GenericItem.vue";

const { server, http } = useServerMock();
vi.mock("@/composables/invocationSelection", () => ({ useInvocationSelection: vi.fn() }));

const selectors = {
    parametersTable: "[data-description='input table']",
    terminalInvocationOutput: "[data-description='terminal invocation output']",
    terminalInvocationOutputItem: "[data-description='terminal invocation output item']",
    nonTerminalInvocationOutput: "[data-description='non-terminal invocation output']",
    nonTerminalInvocationOutputLoading: "[data-description='non-terminal invocation output loading']",
};

// Mock the workflow store to return a workflow for `getStoredWorkflowByInstanceId`
vi.mock("@/stores/workflowStore", async () => {
    const originalModule: any = await vi.importActual("@/stores/workflowStore");
    return {
        ...originalModule,
        useWorkflowStore: () => ({
            ...originalModule.useWorkflowStore(),
            getStoredWorkflowByInstanceId: vi.fn().mockImplementation(() => {
                return {
                    id: "workflow-id",
                    name: "Test Workflow",
                    version: 0,
                };
            }),
            getFullWorkflowCached: vi.fn().mockImplementation(() => {
                /** The actual outputs of the workflow invocation */
                const testDatasetOutputLabels = Object.keys(invocationData.outputs);
                const testCollectionOutputsLabels = Object.keys(invocationData.output_collections);

                return {
                    id: "workflow-id",
                    name: "Test Workflow",
                    version: 0,
                    steps: {
                        "0": {
                            workflow_outputs: testDatasetOutputLabels.map((label) => ({
                                output_name: `output`,
                                label,
                                uuid: `uuid`,
                            })),
                        },
                        "1": {
                            workflow_outputs: testCollectionOutputsLabels.map((label) => ({
                                output_name: `output`,
                                label,
                                uuid: `uuid`,
                            })),
                        },
                    },
                };
            }),
        }),
    };
});

/** Mount the WorkflowInvocationInputOutputTabs component with the given invocation
 * @param invocation The invocation data to be used
 * @param terminal Whether the invocation is terminal
 * @returns The mounted wrapper
 */
async function mountWorkflowInvocationInputOutputTabs(
    invocation: WorkflowInvocationElementView,
    tab: "inputs" | "outputs" = "inputs",
    terminal = true,
) {
    server.use(
        http.get("/api/datasets/{dataset_id}", ({ response, params }) => {
            // We need to use untyped here because this endpoint is not
            // described in the OpenAPI spec due to its complexity for now.
            return response.untyped(
                HttpResponse.json({
                    id: params.dataset_id,
                }),
            );
        }),
        http.get("/api/dataset_collections/{hdca_id}", ({ response, params }) => {
            // We need to use untyped here because this endpoint is not
            // described in the OpenAPI spec due to its complexity for now.
            return response.untyped(
                HttpResponse.json({
                    id: params.hdca_id,
                }),
            );
        }),
    );

    const wrapper = mount(WorkflowInvocationInputOutputTabs as object, {
        props: {
            invocation,
            terminal,
            tab,
        },
        stubs: {
            // ParameterStep renders the actual parameters table (via GTable) from its
            // `parameters` prop rather than a slot, so stubbing it would hide the very
            // rows the "shows invocation inputs" test inspects.
            ContentItem: true,
        },
        pinia: createTestingPinia({ createSpy: vi.fn, stubActions: false }),
    });
    await flushPromises();
    return wrapper;
}

describe("WorkflowInvocationInputOutputTabs", () => {
    it("shows invocation inputs", async () => {
        const wrapper = await mountWorkflowInvocationInputOutputTabs(invocationData as WorkflowInvocationElementView);

        /** The actual parameters are in the input_step_parameters field of the invocation data */
        const testParameters = Object.values({ ...invocationData.input_step_parameters, ...invocationData.inputs });

        // Test that the parameters table is displayed
        const parametersTable = wrapper.find(selectors.parametersTable);
        expect(parametersTable.exists()).toBe(true);

        // Test that the parameters table has the correct number of rows
        const tableParamValues = parametersTable.findAll("tbody tr");
        expect(tableParamValues.length).toEqual(testParameters.length);

        // Test that the parameters are displayed correctly
        for (let i = 0; i < testParameters.length; i++) {
            const testParameter = testParameters[i];
            const tableRow = nth(tableParamValues, i);
            expect(tableRow.find("td").text()).toEqual(testParameter?.label);
            if (testParameter && "parameter_value" in testParameter) {
                expect(nth(tableRow.findAll("td"), 1).text()).toEqual(testParameter.parameter_value.toString());
            }
        }

        /** The actual inputs of the workflow invocation */
        const testInputs = Object.values(invocationData.inputs);

        // Test that the inputs are displayed
        for (let i = 0; i < testInputs.length; i++) {
            const testInput = testInputs[i];
            expect(wrapper.find(`[data-label='${testInput?.label}']`).exists()).toBe(true);
        }
    });

    it("shows invocation outputs when invocation is terminal", async () => {
        const wrapper = await mountWorkflowInvocationInputOutputTabs(
            invocationData as WorkflowInvocationElementView,
            "outputs",
        );

        testOutputsDisplayed(wrapper);
    });

    it("shows workflow output labels when invocation is not terminal", async () => {
        const nonTerminalInvocation = {
            ...invocationData,
            outputs: {},
            output_collections: {},
        } as WorkflowInvocationElementView;
        const wrapper = await mountWorkflowInvocationInputOutputTabs(nonTerminalInvocation, "outputs", false);

        testOutputsDisplayed(wrapper, false);
    });

    function testOutputsDisplayed(wrapper: VueWrapper, terminal = true) {
        /** The actual outputs of the workflow invocation */
        const testDatasetOutputLabels = Object.keys(invocationData.outputs);
        const testCollectionOutputsLabels = Object.keys(invocationData.output_collections);
        const expectedLabels = [...testDatasetOutputLabels, ...testCollectionOutputsLabels];

        // Test that the invocation outputs are displayed
        const invocationOutputs = wrapper.findAll(
            terminal ? selectors.terminalInvocationOutput : selectors.nonTerminalInvocationOutput,
        );
        expect(invocationOutputs.length).toEqual(expectedLabels.length);

        // Test that the output labels are shown
        for (let i = 0; i < invocationOutputs.length; i++) {
            const testOutput = nth(invocationOutputs, i);
            const testLabel = expectedLabels[i];
            expect(testOutput.text()).toContain(testLabel);
            expect(testOutput.find(selectors.terminalInvocationOutputItem).exists()).toBe(terminal);
            expect(testOutput.find(selectors.nonTerminalInvocationOutputLoading).exists()).toBe(!terminal);
        }
    }
});

describe("workflow output URL selection", () => {
    it("expands named datasets and collections and follows selection changes without remounting", async () => {
        const selection: InvocationSelection = {
            stepIndex: ref(null),
            stepTab: ref(undefined),
            job: ref(undefined),
            output: ref("dataset"),
        };
        vi.mocked(useInvocationSelection).mockReturnValue(selection);
        const wrapper = mount(WorkflowInvocationInputOutputTabs, {
            props: {
                invocation: {
                    ...invocationData,
                    outputs: { dataset: { id: "dataset-id", src: "hda", workflow_step_id: "step-1" } },
                    output_collections: {
                        collection: { id: "collection-id", src: "hdca", workflow_step_id: "step-2" },
                    },
                } as WorkflowInvocationElementView,
                tab: "outputs",
                terminal: true,
            },
            global: {
                plugins: [createTestingPinia({ createSpy: vi.fn })],
                stubs: { GenericHistoryItem: true },
            },
        });
        const items = wrapper.findAllComponents(GenericItem);
        expect(items[0]!.props("expanded")).toBe(true);
        expect(items[1]!.props("expanded")).toBeUndefined();
        selection.output.value = "collection";
        await flushPromises();
        expect(items[0]!.props("expanded")).toBeUndefined();
        expect(items[1]!.props("expanded")).toBe(true);
        // Collapsing a different output must not clear the current URL target.
        items[0]!.vm.$emit("update:expanded", false);
        await flushPromises();
        expect(selection.output.value).toBe("collection");
        items[0]!.vm.$emit("update:expanded", true);
        await flushPromises();
        expect(selection.output.value).toBe("dataset");
        items[0]!.vm.$emit("update:expanded", false);
        await flushPromises();
        expect(selection.output.value).toBeUndefined();
        selection.output.value = "unknown";
        await flushPromises();
        expect(items.every((item) => !item.props("expanded"))).toBe(true);
        expect(selection.output.value).toBeUndefined();
        wrapper.unmount();
        vi.mocked(useInvocationSelection).mockReturnValue(undefined);
    });

    it("keeps an output link that a running invocation may still produce", async () => {
        const selection: InvocationSelection = {
            stepIndex: ref(null),
            stepTab: ref(undefined),
            job: ref(undefined),
            output: ref("later"),
        };
        vi.mocked(useInvocationSelection).mockReturnValue(selection);
        const wrapper = mount(WorkflowInvocationInputOutputTabs, {
            props: {
                invocation: { ...invocationData, outputs: {}, output_collections: {} } as WorkflowInvocationElementView,
                tab: "outputs",
                terminal: false,
            },
            global: { plugins: [createTestingPinia({ createSpy: vi.fn })] },
        });
        await flushPromises();
        expect(selection.output.value).toBe("later");
        wrapper.unmount();
        vi.mocked(useInvocationSelection).mockReturnValue(undefined);
    });
});
