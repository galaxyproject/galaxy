import { setActivePinia, createPinia, PiniaVuePlugin } from "pinia";

import { useConnectionStore } from "stores/workflowConnectionStore";
import type { Connection, InputTerminal, OutputTerminal } from "stores/workflowConnectionStore";

const inputTerminal: InputTerminal = {
    stepId: 2,
    name: "input_name",
    connectorType: "input",
};

const outputTerminal: OutputTerminal = {
    stepId: 1,
    name: "output_name",
    connectorType: "output",
};

const connection: Connection = {
    id: "connection-id",
    input: inputTerminal,
    output: outputTerminal,
};

describe("Connection Store", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("adds connection", () => {
        const connectionStore = useConnectionStore();
        expect(connectionStore.connections.length).toBe(0);
        connectionStore.addConnection(connection);
        expect(connectionStore.connections.length).toBe(1);
    });
    it("removes connection", () => {
        const connectionStore = useConnectionStore();
        connectionStore.addConnection(connection);
        connectionStore.removeConnection(inputTerminal);
        expect(connectionStore.connections.length).toBe(0);
    });
});
