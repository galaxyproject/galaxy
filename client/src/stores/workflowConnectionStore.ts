import { defineStore } from "pinia";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

export interface State {
    connections: Connection[];
}

interface Step {
    id: number;
    input_connections: StepInputConnection;
}

interface StepInputConnection {
    [index: string]: {
        output_name: string;
        id: number;
    };
}

export class Connection {
    input: InputTerminal;
    output: OutputTerminal;

    constructor(input: InputTerminal, output: OutputTerminal) {
        this.input = input;
        this.output = output;
    }

    get id(): string {
        return `${this.input.stepId}-${this.input.name}-${this.output.stepId}-${this.output.name}`;
    }
}

export interface BaseTerminal {
    stepId: number;
    name: string;
    connectorType?: "input" | "output";
}

export interface InputTerminal extends BaseTerminal {
    connectorType: "input";
}

export interface OutputTerminal extends BaseTerminal {
    connectorType: "output";
}

interface TerminalToOutputTerminals {
    [index: string]: OutputTerminal[];
}

interface TerminalToInputTerminals {
    [index: string]: InputTerminal[];
}

export const useConnectionStore = defineStore("workflowConnectionStore", {
    state: (): State => ({
        connections: [] as Connection[],
    }),
    getters: {
        getOutputTerminalsForInputTerminal(state: State) {
            const inputTerminalToOutputTerminals: TerminalToOutputTerminals = {};
            state.connections.map((connection) => {
                const terminals = getTerminals(connection);
                const inputTerminalId = getTerminalId(terminals.input);
                inputTerminalId in inputTerminalToOutputTerminals
                    ? inputTerminalToOutputTerminals[inputTerminalId].push(terminals.output)
                    : (inputTerminalToOutputTerminals[inputTerminalId] = [terminals.output]);
            });
            return (terminalId: string): OutputTerminal[] => {
                return inputTerminalToOutputTerminals[terminalId] || [];
            };
        },
        getInputTerminalsForOutputTerminal(state: State) {
            const outputTerminalToInputTerminals: TerminalToInputTerminals = {};
            state.connections.map((connection) => {
                const terminals = getTerminals(connection);
                const outputTerminalId = getTerminalId(terminals.output);
                outputTerminalId in outputTerminalToInputTerminals
                    ? outputTerminalToInputTerminals[outputTerminalId].push(terminals.input)
                    : (outputTerminalToInputTerminals[outputTerminalId] = [terminals.input]);
            });
            return (terminalId: string): BaseTerminal[] => {
                return outputTerminalToInputTerminals[terminalId] || [];
            };
        },
        getConnectionsForTerminal(state: State) {
            const terminalToConnection: { [index: string]: Connection[] } = {};
            state.connections.map((connection) => {
                const terminals = getTerminals(connection);
                const outputTerminalId = getTerminalId(terminals.output);
                if (outputTerminalId in terminalToConnection) {
                    terminalToConnection[outputTerminalId].push(connection);
                } else {
                    terminalToConnection[outputTerminalId] = [connection];
                }
                const inputTerminalId = getTerminalId(terminals.input);
                if (inputTerminalId in terminalToConnection) {
                    terminalToConnection[inputTerminalId].push(connection);
                } else {
                    terminalToConnection[inputTerminalId] = [connection];
                }
            });
            return (terminalId: string): Connection[] => {
                return terminalToConnection[terminalId] || [];
            };
        },
        getConnectionsForStep(state: State) {
            const stepToConnections: { [index: number]: Connection[] } = {};
            state.connections.map((connection) => {
                connection.input.stepId in stepToConnections
                    ? stepToConnections[connection.input.stepId].push(connection)
                    : (stepToConnections[connection.input.stepId] = [connection]);
                connection.output.stepId in stepToConnections
                    ? stepToConnections[connection.output.stepId].push(connection)
                    : (stepToConnections[connection.output.stepId] = [connection]);
            });
            return (stepId: number): Connection[] => stepToConnections[stepId] || [];
        },
    },
    actions: {
        addConnection(this: State, connection: Connection) {
            this.connections.push(connection);
            const stepStore = useWorkflowStepStore();
            stepStore.addConnection(connection);
        },
        removeConnection(this: State, terminal: InputTerminal | OutputTerminal | Connection["id"]) {
            const stepStore = useWorkflowStepStore();
            this.connections = this.connections.filter((connection) => {
                if (typeof terminal === "string") {
                    if (connection.id == terminal) {
                        stepStore.removeConnection(connection);
                        return false;
                    } else {
                        return true;
                    }
                } else if (terminal.connectorType === "input") {
                    if (connection.input.stepId == terminal.stepId && connection.input.name == terminal.name) {
                        stepStore.removeConnection(connection);
                        return false;
                    } else {
                        return true;
                    }
                } else {
                    if (connection.output.stepId == terminal.stepId && connection.output.name == terminal.name) {
                        stepStore.removeConnection(connection);
                        return false;
                    } else {
                        return true;
                    }
                }
            });
        },
    },
});

export function getTerminalId(item: BaseTerminal): string {
    return `node-${item.stepId}-${item.connectorType}-${item.name}`;
}

export function getTerminals(item: Connection): { input: InputTerminal; output: OutputTerminal } {
    return {
        input: { stepId: item.input.stepId, name: item.input.name, connectorType: "input" },
        output: { stepId: item.output.stepId, name: item.output.name, connectorType: "output" },
    };
}
