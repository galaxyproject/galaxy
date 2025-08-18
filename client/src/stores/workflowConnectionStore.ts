import { computed, del, ref, set } from "vue";

import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { pushOrSet } from "@/utils/pushOrSet";

import { defineScopedStore } from "./scopedStore";
import type {
    BaseTerminal,
    Connection,
    ConnectionId,
    InputTerminal,
    InvalidConnections,
    OutputTerminal,
    TerminalToOutputTerminals,
} from "./workflowStoreTypes";

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

export type WorkflowConnectionStore = ReturnType<typeof useConnectionStore>;

export const useConnectionStore = defineScopedStore("workflowConnectionStore", (workflowId) => {
    const connections = ref<Readonly<Connection>[]>([]);
    const invalidConnections = ref<InvalidConnections>({});
    const inputTerminalToOutputTerminals = ref<TerminalToOutputTerminals>({});
    const terminalToConnection = ref<{ [index: string]: Connection[] }>({});
    const stepToConnections = ref<{ [index: number]: Connection[] }>({});

    function $reset() {
        connections.value = [];
        invalidConnections.value = {};
        inputTerminalToOutputTerminals.value = {};
        terminalToConnection.value = {};
        stepToConnections.value = {};
    }

    const getOutputTerminalsForInputTerminal = computed(
        () => (terminalId: string) => inputTerminalToOutputTerminals.value[terminalId] || ([] as OutputTerminal[])
    );

    const getConnectionsForTerminal = computed(
        () => (terminalId: string) => terminalToConnection.value[terminalId] || ([] as Connection[])
    );

    const getConnectionsForStep = computed(
        () => (stepId: number) => stepToConnections.value[stepId] || ([] as Connection[])
    );

    const stepStore = useWorkflowStepStore(workflowId);

    function addConnection(connection: Connection) {
        Object.freeze(connection);
        connections.value.push(connection);
        stepStore.addConnection(connection);

        terminalToConnection.value = updateTerminalToConnection(connections.value);
        inputTerminalToOutputTerminals.value = updateTerminalToTerminal(connections.value);
        stepToConnections.value = updateStepToConnections(connections.value);
    }

    function removeConnection(terminal: InputTerminal | OutputTerminal | ConnectionId) {
        connections.value = connections.value.filter((connection) => {
            const id = getConnectionId(connection);

            if (typeof terminal === "string") {
                if (id === terminal) {
                    stepStore.removeConnection(connection);
                    del(invalidConnections.value, id);
                    return false;
                } else {
                    return true;
                }
            } else if (terminal.connectorType === "input") {
                if (connection.input.stepId == terminal.stepId && connection.input.name == terminal.name) {
                    stepStore.removeConnection(connection);
                    del(invalidConnections.value, id);
                    return false;
                } else {
                    return true;
                }
            } else {
                if (connection.output.stepId == terminal.stepId && connection.output.name == terminal.name) {
                    stepStore.removeConnection(connection);
                    del(invalidConnections.value, id);
                    return false;
                } else {
                    return true;
                }
            }
        });

        terminalToConnection.value = updateTerminalToConnection(connections.value);
        inputTerminalToOutputTerminals.value = updateTerminalToTerminal(connections.value);
        stepToConnections.value = updateStepToConnections(connections.value);
    }

    function markInvalidConnection(connectionId: string, reason: string) {
        set(invalidConnections.value, connectionId, reason);
    }

    function dropFromInvalidConnections(connectionId: string) {
        del(invalidConnections.value, connectionId);
    }

    return {
        connections,
        invalidConnections,
        inputTerminalToOutputTerminals,
        terminalToConnection,
        stepToConnections,
        $reset,
        getOutputTerminalsForInputTerminal,
        getConnectionsForTerminal,
        getConnectionsForStep,
        addConnection,
        removeConnection,
        markInvalidConnection,
        dropFromInvalidConnections,
    };
});
