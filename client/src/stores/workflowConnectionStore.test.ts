import { beforeEach, describe, expect, it } from "vitest";

import { getTerminalId, useConnectionStore } from "@/stores/workflowConnectionStore";
import { type NewStep, useWorkflowStepStore } from "@/stores/workflowStepStore";
import type { Connection, InputTerminal, OutputTerminal } from "@/stores/workflowStoreTypes";

import { setupTestPinia } from "./testUtils";

const workflowStepZero: NewStep = {
    input_connections: {},
    inputs: [],
    name: "a step",
    outputs: [],
    post_job_actions: {},
    tool_state: {},
    type: "tool",
    workflow_outputs: [],
};

const workflowStepOne: NewStep = { ...workflowStepZero };

const inputTerminal: InputTerminal = {
    stepId: 1,
    name: "input_name",
    connectorType: "input",
};

const outputTerminal: OutputTerminal = {
    stepId: 0,
    name: "output_name",
    connectorType: "output",
};

const connection: Connection = {
    input: inputTerminal,
    output: outputTerminal,
};

describe("Connection Store", () => {
    beforeEach(() => {
        setupTestPinia();
        const workflowStepStore = useWorkflowStepStore("mock-workflow");
        workflowStepStore.addStep(workflowStepZero);
        workflowStepStore.addStep(workflowStepOne);
    });

    it("adds a connection to an empty workflow", () => {
        const connectionStore = useConnectionStore("mock-workflow");
        expect(connectionStore.connections).toHaveLength(0);
        connectionStore.addConnection(connection);
        expect(connectionStore.connections).toHaveLength(1);
    });
    it("removes a connection using its input terminal", () => {
        const connectionStore = useConnectionStore("mock-workflow");
        connectionStore.addConnection(connection);
        connectionStore.removeConnection(inputTerminal);
        expect(connectionStore.connections).toHaveLength(0);
    });
    it("indexes a connection under both steps and clears both indexes on removal", () => {
        const connectionStore = useConnectionStore("mock-workflow");
        expect(connectionStore.getConnectionsForStep(0)).toStrictEqual([]);
        expect(connectionStore.getConnectionsForStep(1)).toStrictEqual([]);
        connectionStore.addConnection(connection);
        expect(connectionStore.getConnectionsForStep(0)).toStrictEqual([connection]);
        expect(connectionStore.getConnectionsForStep(1)).toStrictEqual([connection]);
        connectionStore.removeConnection(connection.input);
        expect(connectionStore.getConnectionsForStep(0)).toStrictEqual([]);
        expect(connectionStore.getConnectionsForStep(1)).toStrictEqual([]);
    });
    it("indexes output terminals by input terminal and clears the index on removal", () => {
        const connectionStore = useConnectionStore("mock-workflow");
        expect(connectionStore.getOutputTerminalsForInputTerminal(getTerminalId(connection.input))).toStrictEqual([]);
        connectionStore.addConnection(connection);
        expect(connectionStore.getOutputTerminalsForInputTerminal(getTerminalId(connection.input))).toStrictEqual([
            connection.output,
        ]);
        connectionStore.removeConnection(connection.input);
        expect(connectionStore.getOutputTerminalsForInputTerminal(getTerminalId(connection.input))).toStrictEqual([]);
    });
});
