import { createPinia, setActivePinia } from "pinia";

import {
    type Connection,
    getTerminalId,
    type InputTerminal,
    type OutputTerminal,
    useConnectionStore,
} from "@/stores/workflowConnectionStore";
import { type NewStep, useWorkflowStepStore } from "@/stores/workflowStepStore";

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
        setActivePinia(createPinia());
        const workflowStepStore = useWorkflowStepStore("mock-workflow");
        workflowStepStore.addStep(workflowStepZero);
        workflowStepStore.addStep(workflowStepOne);
    });

    it("adds connection", () => {
        const connectionStore = useConnectionStore("mock-workflow");
        expect(connectionStore.connections.length).toBe(0);
        connectionStore.addConnection(connection);
        expect(connectionStore.connections.length).toBe(1);
    });
    it("removes connection", () => {
        const connectionStore = useConnectionStore("mock-workflow");
        connectionStore.addConnection(connection);
        connectionStore.removeConnection(inputTerminal);
        expect(connectionStore.connections.length).toBe(0);
    });
    it("finds connections for steps", () => {
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
    it("finds output terminals for input terminal", () => {
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
