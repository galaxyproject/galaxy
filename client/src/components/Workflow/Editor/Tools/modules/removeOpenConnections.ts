import type { ConnectionOutputLink, Step } from "@/stores/workflowStepStore";

export function removeOpenConnections(steps: Step[]) {
    const stepIdSet = new Set(steps.map((step) => step.id));

    const stepEntriesWithFilteredInputs: Step[] = steps.map((step) => {
        const connectionEntries = Object.entries(step.input_connections);

        const filteredConnectionEntries: [string, ConnectionOutputLink[]][] = connectionEntries.flatMap(
            ([id, connection]) => {
                if (!connection) {
                    return [];
                }

                const connectionArray = Array.isArray(connection) ? connection : [connection];
                const filteredConnectionArray = connectionArray.filter((connection) => stepIdSet.has(connection.id));

                if (filteredConnectionArray.length === 0) {
                    return [];
                } else {
                    return [[id, filteredConnectionArray]];
                }
            }
        );

        const input_connections = Object.fromEntries(filteredConnectionEntries);

        return { ...step, input_connections };
    });

    return stepEntriesWithFilteredInputs;
}
