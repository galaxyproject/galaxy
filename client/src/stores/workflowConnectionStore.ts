import { defineStore } from "pinia";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { pushOrSet } from "@/utils/pushOrSet";
import Vue from "vue";

interface InvalidConnections {
    [index: ConnectionId]: string | undefined;
}

export interface State {
    connections: Connection[];
    invalidConnections: InvalidConnections;
    inputTerminalToOutputTerminals: TerminalToOutputTerminals;
    terminalToConnection: { [index: string]: Connection[] };
    stepToConnections: { [index: number]: Connection[] };
}

export interface Connection {
    input: InputTerminal;
    output: OutputTerminal;
}

export type ConnectionId = `${string}-${string}-${string}-${string}`;

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

export const useConnectionStore = defineStore("workflowConnectionStore", {
    state: (): State => ({
        connections: [] as Array<Readonly<Connection>>,
        invalidConnections: {} as InvalidConnections,
        inputTerminalToOutputTerminals: {} as TerminalToOutputTerminals,
        terminalToConnection: {} as { [index: string]: Connection[] },
        stepToConnections: {} as { [index: number]: Connection[] },
    }),
    getters: {
        getOutputTerminalsForInputTerminal(state: State) {
            return (terminalId: string): OutputTerminal[] => {
                return state.inputTerminalToOutputTerminals[terminalId] || [];
            };
        },
        getConnectionsForTerminal(state: State) {
            return (terminalId: string): Connection[] => {
                return state.terminalToConnection[terminalId] || [];
            };
        },
        getConnectionsForStep(state: State) {
            return (stepId: number): Connection[] => state.stepToConnections[stepId] || [];
        },
    },
    actions: {
        addConnection(this, _connection: Connection) {
            const connection = Object.freeze(_connection);
            this.connections.push(connection);
            const stepStore = useWorkflowStepStore();
            stepStore.addConnection(connection);
            this.terminalToConnection = updateTerminalToConnection(this.connections);
            this.inputTerminalToOutputTerminals = updateTerminalToTerminal(this.connections);
            this.stepToConnections = updateStepToConnections(this.connections);
        },
        markInvalidConnection(this: State, connectionId: string, reason: string) {
            Vue.set(this.invalidConnections, connectionId, reason);
        },
        dropFromInvalidConnections(this: State, connectionId: string) {
            Vue.delete(this.invalidConnections, connectionId);
        },
        removeConnection(this, terminal: InputTerminal | OutputTerminal | ConnectionId) {
            const stepStore = useWorkflowStepStore();
            this.connections = this.connections.filter((connection) => {
                const id = getConnectionId(connection);

                if (typeof terminal === "string") {
                    if (id === terminal) {
                        stepStore.removeConnection(connection);
                        Vue.delete(this.invalidConnections, id);
                        return false;
                    } else {
                        return true;
                    }
                } else if (terminal.connectorType === "input") {
                    if (connection.input.stepId == terminal.stepId && connection.input.name == terminal.name) {
                        stepStore.removeConnection(connection);
                        Vue.delete(this.invalidConnections, id);
                        return false;
                    } else {
                        return true;
                    }
                } else {
                    if (connection.output.stepId == terminal.stepId && connection.output.name == terminal.name) {
                        stepStore.removeConnection(connection);
                        Vue.delete(this.invalidConnections, id);
                        return false;
                    } else {
                        return true;
                    }
                }
            });
            this.terminalToConnection = updateTerminalToConnection(this.connections);
            this.inputTerminalToOutputTerminals = updateTerminalToTerminal(this.connections);
            this.stepToConnections = updateStepToConnections(this.connections);
        },
    },
});

function updateTerminalToTerminal(connections: Connection[]) {
    const inputTerminalToOutputTerminals: TerminalToOutputTerminals = {};
    connections.forEach((connection) => {
        const terminals = getTerminals(connection);
        const inputTerminalId = getTerminalId(terminals.input);
        pushOrSet(inputTerminalToOutputTerminals, inputTerminalId, terminals.output);
    });
    return inputTerminalToOutputTerminals;
}

function updateTerminalToConnection(connections: Connection[]) {
    const terminalToConnection: { [index: string]: Connection[] } = {};
    connections.forEach((connection) => {
        const terminals = getTerminals(connection);
        const outputTerminalId = getTerminalId(terminals.output);
        pushOrSet(terminalToConnection, outputTerminalId, connection);
        const inputTerminalId = getTerminalId(terminals.input);
        pushOrSet(terminalToConnection, inputTerminalId, connection);
    });
    return terminalToConnection;
}

function updateStepToConnections(connections: Connection[]) {
    const stepToConnections: { [index: number]: Connection[] } = {};
    connections.forEach((connection) => {
        pushOrSet(stepToConnections, connection.input.stepId, connection);
        pushOrSet(stepToConnections, connection.output.stepId, connection);
    });
    return stepToConnections;
}

export function getTerminalId(item: BaseTerminal): string {
    return `node-${item.stepId}-${item.connectorType}-${item.name}`;
}

export function getTerminals(item: Connection): { input: InputTerminal; output: OutputTerminal } {
    return {
        input: { stepId: item.input.stepId, name: item.input.name, connectorType: "input" },
        output: { stepId: item.output.stepId, name: item.output.name, connectorType: "output" },
    };
}

export function getConnectionId(item: Connection): ConnectionId {
    return `${item.input.stepId}-${item.input.name}-${item.output.stepId}-${item.output.name}`;
}
