import type { ConnectionOutputLink, Step } from "@/stores/workflowStepStore";

export function onAllInputs(step: Step, callback: (connection: ConnectionOutputLink, name: string) => void) {
    Object.entries(step.input_connections).forEach(([name, connection]) => {
        if (connection) {
            const connectionArray = Array.isArray(connection) ? connection : [connection];
            connectionArray.forEach((connection) => callback(connection, name));
        }
    });
}
