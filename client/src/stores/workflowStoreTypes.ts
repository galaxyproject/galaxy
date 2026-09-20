export interface TerminalToOutputTerminals {
    [index: string]: OutputTerminal[];
}

export interface InvalidConnections {
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
