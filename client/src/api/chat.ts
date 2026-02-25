import { rethrowSimple } from "@/utils/simple-error";

import { GalaxyApi } from "./client";

export async function generateAIReport(workflowId: string, version?: number, instance?: boolean) {
    const { data, error } = await GalaxyApi().GET("/api/chat/{workflow_id}/generate_report", {
        params: {
            path: { workflow_id: workflowId },
            query: {
                version: version,
                instance: instance,
            },
        },
    });
    if (error) {
        rethrowSimple(error);
    }

    return data as string;
}
