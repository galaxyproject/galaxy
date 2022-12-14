import { defineStore } from "pinia";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

interface State {
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

export interface Connection {
    id: string;
    input: InputTerminal;
    output: OutputTerminal;
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

interface TerminalToTerminal {
    [index: string]: BaseTerminal[];
}

export const useConnectionStore = defineStore("workflowConnectionStore", {
    state: (): State => ({
        connections: [] as Connection[],
    }),
    getters: {
        getOutputTerminalsForInputTerminal(state: State) {
            const inputTerminalToOutputTerminals: TerminalToTerminal = {};
            state.connections.map((connection) => {
                const terminals = getTerminals(connection);
                const inputTerminalId = getTerminalId(terminals.input);
                inputTerminalId in inputTerminalToOutputTerminals
                    ? inputTerminalToOutputTerminals[inputTerminalId].push(terminals.output)
                    : (inputTerminalToOutputTerminals[inputTerminalId] = [terminals.output]);
            });
            return (terminalId: string): BaseTerminal[] => {
                return inputTerminalToOutputTerminals[terminalId] || [];
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
        removeConnection(this: State, terminal: InputTerminal | OutputTerminal) {
            const stepStore = useWorkflowStepStore();
            this.connections = this.connections.filter((connection) => {
                if (terminal.connectorType === "input") {
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

export function getTerminals(item: Connection): { input: BaseTerminal; output: BaseTerminal } {
    return {
        input: { stepId: item.input.stepId, name: item.input.name, connectorType: "input" },
        output: { stepId: item.output.stepId, name: item.output.name, connectorType: "output" },
    };
}
