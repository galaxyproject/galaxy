import type { ConnectionOutputLink, Step } from "@/stores/workflowStepStore";

/** Loop through all input_connections of a step */
export function onAllInputs(step: Step, callback: (connection: ConnectionOutputLink, name: string) => void) {
    Object.entries(step.input_connections).forEach(([name, connection]) => {
        if (connection) {
            const connectionArray = Array.isArray(connection) ? connection : [connection];
            connectionArray.forEach((connection) => callback(connection, name));
        }
    });
}
