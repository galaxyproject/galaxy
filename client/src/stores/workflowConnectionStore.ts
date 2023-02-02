import { defineStore } from "pinia";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import Vue from "vue";

interface InvalidConnections {
    [index: string]: string | undefined;
}

export interface State {
    connections: Connection[];
    invalidConnections: InvalidConnections;
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
    input_subworkflow_step_id?: number;
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

/**
 * Pushes a value to an array in an object, if the array exists. Else creates a new array containing value.
 * @param object Object which contains array
 * @param key Key which array is in
 * @param value Value to push
 */
function pushOrSet<T>(object: { [key: string | number]: Array<T> }, key: string | number, value: T) {
    if (key in object) {
        object[key]!.push(value);
    } else {
        object[key] = [value];
    }
}

export const useConnectionStore = defineStore("workflowConnectionStore", {
    state: (): State => ({
        connections: [] as Connection[],
        invalidConnections: {} as InvalidConnections,
    }),
    getters: {
        getOutputTerminalsForInputTerminal(state: State) {
            const inputTerminalToOutputTerminals: TerminalToOutputTerminals = {};
            state.connections.map((connection) => {
                const terminals = getTerminals(connection);
                const inputTerminalId = getTerminalId(terminals.input);
                pushOrSet(inputTerminalToOutputTerminals, inputTerminalId, terminals.output);
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
                pushOrSet(outputTerminalToInputTerminals, outputTerminalId, terminals.input);
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
                pushOrSet(terminalToConnection, outputTerminalId, connection);

                const inputTerminalId = getTerminalId(terminals.input);
                pushOrSet(terminalToConnection, inputTerminalId, connection);
            });
            return (terminalId: string): Connection[] => {
                return terminalToConnection[terminalId] || [];
            };
        },
        getConnectionsForStep(state: State) {
            const stepToConnections: { [index: number]: Connection[] } = {};
            state.connections.map((connection) => {
                pushOrSet(stepToConnections, connection.input.stepId, connection);
                pushOrSet(stepToConnections, connection.output.stepId, connection);
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
        markInvalidConnection(this: State, connectionId: string, reason: string) {
            Vue.set(this.invalidConnections, connectionId, reason);
        },
        dropFromInvalidConnections(this: State, connectionId: string) {
            Vue.delete(this.invalidConnections, connectionId);
        },
        removeConnection(this: State, terminal: InputTerminal | OutputTerminal | Connection["id"]) {
            const stepStore = useWorkflowStepStore();
            this.connections = this.connections.filter((connection) => {
                if (typeof terminal === "string") {
                    if (connection.id == terminal) {
                        stepStore.removeConnection(connection);
                        Vue.delete(this.invalidConnections, connection.id);
                        return false;
                    } else {
                        return true;
                    }
                } else if (terminal.connectorType === "input") {
                    if (connection.input.stepId == terminal.stepId && connection.input.name == terminal.name) {
                        stepStore.removeConnection(connection);
                        Vue.delete(this.invalidConnections, connection.id);
                        return false;
                    } else {
                        return true;
                    }
                } else {
                    if (connection.output.stepId == terminal.stepId && connection.output.name == terminal.name) {
                        stepStore.removeConnection(connection);
                        Vue.delete(this.invalidConnections, connection.id);
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
