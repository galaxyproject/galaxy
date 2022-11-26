import { defineStore } from "pinia";

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
    input: {
        stepId: number;
        name: string;
    };
    output: {
        stepId: number;
        name: string;
    };
}

export interface BaseTerminal {
    stepId: number;
    name: string;
    connectorType: "input" | "output";
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
            const inputTerminalToOutputTerminals = {};
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
    },
    actions: {
        addConnection(this: State, connection: Connection) {
            this.connections.push(connection);
        },
        removeConnection(this: State, inputTerminal: InputTerminal) {
            this.connections = this.connections.filter(
                (connection) =>
                    connection.input.stepId != inputTerminal.stepId || connection.input.name != inputTerminal.name
            );
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
