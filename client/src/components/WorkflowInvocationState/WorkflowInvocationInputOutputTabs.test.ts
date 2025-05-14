import { createTestingPinia } from "@pinia/testing";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { WorkflowInvocationElementView } from "@/api/invocations";

import invocationData from "../Workflow/test/json/invocation.json";

import WorkflowInvocationInputOutputTabs from "./WorkflowInvocationInputOutputTabs.vue";

const { server, http } = useServerMock();

const selectors = {
    parametersTable: "[data-description='input table']",
    terminalInvocationOutput: "[data-description='terminal invocation output']",
    terminalInvocationOutputItem: "[data-description='terminal invocation output item']",
    nonTerminalInvocationOutput: "[data-description='non-terminal invocation output']",
    nonTerminalInvocationOutputLoading: "[data-description='non-terminal invocation output loading']",
};

// Mock the workflow store to return a workflow for `getStoredWorkflowByInstanceId`
jest.mock("@/stores/workflowStore", () => {
    const originalModule = jest.requireActual("@/stores/workflowStore");
    return {
        ...originalModule,
        useWorkflowStore: () => ({
            ...originalModule.useWorkflowStore(),
            getStoredWorkflowByInstanceId: jest.fn().mockImplementation(() => {
                return {
                    id: "workflow-id",
                    name: "Test Workflow",
                    version: 0,
                };
            }),
            getFullWorkflowCached: jest.fn().mockImplementation(() => {
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
async function mountWorkflowInvocationInputOutputTabs(invocation: WorkflowInvocationElementView, terminal = true) {
    server.use(
        http.get("/api/datasets/{dataset_id}", ({ response, params }) => {
            // We need to use untyped here because this endpoint is not
            // described in the OpenAPI spec due to its complexity for now.
            return response.untyped(
                HttpResponse.json({
                    id: params.dataset_id,
                })
            );
        }),
        http.get("/api/dataset_collections/{hdca_id}", ({ response, params }) => {
            // We need to use untyped here because this endpoint is not
            // described in the OpenAPI spec due to its complexity for now.
            return response.untyped(
                HttpResponse.json({
                    id: params.hdca_id,
                })
            );
        })
    );

    const wrapper = mount(WorkflowInvocationInputOutputTabs as object, {
        propsData: {
            invocation,
            terminal,
        },
        stubs: {
            ContentItem: true,
            ParameterStep: true,
        },
        pinia: createTestingPinia(),
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
            const tableRow = tableParamValues.at(i);
            expect(tableRow.find("td").text()).toEqual(testParameter?.label);
            if (testParameter && "parameter_value" in testParameter) {
                expect(tableRow.findAll("td").at(1).text()).toEqual(testParameter.parameter_value.toString());
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
        const wrapper = await mountWorkflowInvocationInputOutputTabs(invocationData as WorkflowInvocationElementView);

        testOutputsDisplayed(wrapper);
    });

    it("shows workflow output labels when invocation is not terminal", async () => {
        const nonTerminalInvocation = {
            ...invocationData,
            outputs: {},
            output_collections: {},
        } as WorkflowInvocationElementView;
        const wrapper = await mountWorkflowInvocationInputOutputTabs(nonTerminalInvocation, false);

        testOutputsDisplayed(wrapper, false);
    });

    function testOutputsDisplayed(wrapper: Wrapper<Vue>, terminal = true) {
        /** The actual outputs of the workflow invocation */
        const testDatasetOutputLabels = Object.keys(invocationData.outputs);
        const testCollectionOutputsLabels = Object.keys(invocationData.output_collections);
        const expectedLabels = [...testDatasetOutputLabels, ...testCollectionOutputsLabels];

        // Test that the invocation outputs are displayed
        const invocationOutputs = wrapper.findAll(
            terminal ? selectors.terminalInvocationOutput : selectors.nonTerminalInvocationOutput
        );
        expect(invocationOutputs.length).toEqual(expectedLabels.length);

        // Test that the output labels are shown
        for (let i = 0; i < invocationOutputs.length; i++) {
            const testOutput = invocationOutputs.at(i);
            const testLabel = expectedLabels[i];
            expect(testOutput.text()).toContain(testLabel);
            expect(testOutput.find(selectors.terminalInvocationOutputItem).exists()).toBe(terminal);
            expect(testOutput.find(selectors.nonTerminalInvocationOutputLoading).exists()).toBe(!terminal);
        }
    }
});
